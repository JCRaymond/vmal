# VMALAssembler.py
import re

# Dictionary mapping VMAL operation mnemonics to their internal numeric codes
# This is used to identify and validate operations during parsing
op_map = {
    'SA': 0,  # Set Address (load MAR from register)
    'RB': 1,  # Read Buffer (load register from MBR)
    'RD': 2,  # Read (load MBR from memory at MAR)
    'WR': 3,  # Write (store MBR to memory at MAR)
    'SB': 4,  # Set Buffer (load MBR from register)
    'SF': 5,  # Set Flags (set N and Z flags based on register)
    'LBL': -1,  # Label (pseudo-operation for defining jump targets)
    'GO': 6,  # Go (unconditional jump to label)
    'BIN': 7,  # Branch If Negative (conditional jump if N flag is set)
    'BIZ': 8,  # Branch If Zero (conditional jump if Z flag is set)
    'ADD': 9,  # Add (add two registers)
    'AND': 10,  # Bitwise AND (between two registers)
    'MV': 11,  # Move (copy from one register to another)
    'NOT': 12,  # Bitwise NOT (invert bits of register)
    'RS': 13,  # Right Shift (shift register right by 1 bit)
    'LS': 14,  # Left Shift (shift register left by 1 bit)
    'SW': 15  # Store Word (combined SA, SB, WR operations)
}

# Sets defining operation categories based on argument requirements
# These help in validating the number and type of arguments for each op during assembly
label_ops = {-1, 6, 7, 8}  # Operations involving labels (e.g., jumps or definitions)
zero_arg_ops = {2, 3}  # Operations with no arguments (e.g., RD, WR)
one_reg_ops = {0, 1, 4, 5}  # Operations requiring one register argument
two_reg_ops = {9, 10, 11, 12, 13, 14, 15}  # Operations requiring two register arguments


# Helper function to print assembly errors with line context
# This ensures users get clear feedback on syntax issues during assembly
def printerror(i, line, msg):
    """Print a formatted error message with line number and context."""
    print(f'Error on line #{i+1}: {msg}')
    print(f'\t> {line}')


# Function to parse numeric literals (hex, binary, decimal) from VMAL code
# Used for register/memory initializers and potentially other numeric args
def parse_number(s):
    """
    Parse a number from a string, supporting decimal, hex (0x), and binary (0b) formats.
    Returns a tuple of (parsed_value, error_message).
    If parsing fails, parsed_value is None and error_message contains the error.
    """
    # Hexadecimal
    if s[:2] == '0x':
        try:
            return int(s[2:], 16), None
        except ValueError:
            return None, 'Invalid hexadecimal literal in {} initializer - "{}"'
    # Binary
    if s[:2] == '0b':
        try:
            return int(s[2:], 2), None
        except ValueError:
            return None, 'Invalid binary literal in {} initializer - "{}"'
    # Decimal
    try:
        return int(s), None
    except ValueError:
        return None, 'Invalid character sequence in {} initializer - "{}"'


# Regular expression for validating label names (must match C-style identifiers).
# Ensures labels are properly formatted during assembly
is_cname = re.compile('[_a-zA-Z][_a-zA-Z0-9]*')


# Main assembly steps:
# 1. Reads and parses each line, handling comments, initializers, and instructions.
# 2. Validates syntax, operations, and arguments.
# 3. Builds lists for instructions, register initializations, and memory initializations.
# 4. Tracks and resolves labels for jumps.
# 5. Returns assembled machine code or None if errors occur.
def assemble(f):
    """
    Assemble VMAL code from a file-like object.
    
    Returns a tuple of (instructions, reg_inits, mem_inits) if successful,
    or None if assembly fails due to errors.
    
    The assembly process has two passes:
    1. Parse all instructions and build the label map
    2. Resolve label references and generate final machine code
    """
    reg_inits = []  # List of (register, value) tuples for register initialization
    mem_inits = []  # List of (address, value) tuples for memory initialization
    instructions = []  # List of parsed instructions (op_code, *args)
    lbl_lines = {}  # Maps instruction index to (line_number, line_text) for error reporting
    label_map = {}  # Maps label names to instruction indices

    # First pass: Remove comments and empty lines, parse instructions,
    #             and build label map for second pass
    for i, line in enumerate(f):
        # Strip comments and leading/trailing whitespace to isolate code
        code, _, comment = line.partition('#')
        del comment
        code = code.strip()
        if not code:
            continue  # Skip empty lines

        # Split code at semicolon (required terminator)
        code, semicol, rest = code.partition(';')
        if semicol != ';':
            printerror(i, line, 'Missing semicolon')
            return None
        rest = rest.strip()
        # Error if there are characters after a semicolon
        if rest:
            printerror(i, line, f'Extra non-comment character sequence after semicolon - "{rest}"')
            return None

        # Check for register/memory initializers (e.g., 'A: 5;' or '[0x10]: 42;')
        # These can be identified by a colon
        bpart, col, epart = code.partition(':')
        if col == ':':
            loc = bpart.strip()
            val = epart.strip()
            is_reg_init = False
            msg = ''
            # Parse register initializers (single hex digit, e.g., 'A' for 10)
            if len(loc) == 1:
                try:
                    reg = int(loc, 16)
                except ValueError:
                    printerror(i, line, f'Invalid register in register initializer - "{loc}"')
                    return None
                is_reg_init = True
                msg = 'register'
            # Parse memory initializers (e.g., '[0x100]')
            elif loc[0] == '[' and loc[-1] == ']':
                mem = loc[1:-1]
                mem, err = parse_number(mem)
                if mem is None:
                    printerror(i, line, err.format('memory', mem))
                    return None
                msg = 'memory'
            else:
                printerror(i, line, 'Invalid syntax for register/memory initializer')
                return None
            # Parse the value for the initializer
            val, err = parse_number(val)
            if val is None:
                printerror(i, line, err.format(msg, val))
                return None
            # Add to appropriate initialization list
            if is_reg_init:
                reg_inits.append((reg, val))
            else:
                mem_inits.append((mem, val))
            continue  # Move to the next line after handling initializer

        # Parse operations/instructions (e.g., 'MV E, 6;')
        # Split into opcode and arguments
        op, space, args = code.strip().partition(' ')
        op = op.upper()  # Standardize opcode to uppercase for matching

        # Validate that the line follows the convention of "OP( ARGS)"
        if op != 'RD' and op != 'WR' and space != ' ':
            printerror(i, line, f'Unknown character sequence "{op}"')
            return None
        # Validate that the operation is a valid operation
        if op not in op_map:
            printerror(i, line, f'Unknown operation "{op}"')
            return None
        op_num = op_map[op]  # Get the numeric code for the operation
        # Split and clean arguments (comma-separated)
        args = [arg.strip() for arg in args.split(',') if len(arg.strip()) > 0]

        # Handle label-related operations (LBL, GO, BIN, BIZ)
        # These may define labels or reference them for jumps
        if op_num in label_ops:
            if len(args) > 1:
                printerror(i, line, f'Too many arguments for {op} operation (expected 1 label, got {len(args)} args)')
                return None
            if len(args) < 1:
                printerror(i, line, f'Not enough arguments for {op} operation (expected 1 label, got {len(args)} args)')
                return None
            lbl = args[0]

            # Special handling for LBL pseudo-operation
            if op_num == -1:
                match = is_cname.fullmatch(lbl)
                if match is None:
                    printerror(i, line, f'Label name is not a valid cname - "{lbl}"')
                    return None
                # Check that label has not already been defined to prevent redefinition
                if lbl in label_map:
                    printerror(i, line, f'Label "{lbl}" already defined')
                    return None
                # Map the label to the previous instruction index for later resolution
                # Program counter incrementation occurs at the start of every cycle,
                # so any jump instruction should go to the instruction before a label
                label_map[lbl] = len(instructions) - 1
                continue
            # For jump operations track the line and line number for future error printing
            lbl_lines[len(instructions)] = (i, line)
            instructions.append((op_num, lbl))
            continue

        # Handle operations with no arguments (RD, WR)
        if op_num in zero_arg_ops:
            if len(args) > 0:
                printerror(i, line, f'Too many arguments for {op} operation (expected no arguments, got {len(args)} args)')
                return None
            instructions.append((op_num, ))
            continue

        # Handle operations with one register argument (SA, RB, SB, SF)
        if op_num in one_reg_ops:
            if len(args) > 1:
                printerror(i, line, f'Too many arguments for {op} operation (expected 1 register, got {len(args)} args)')
                return None
            if len(args) < 1:
                printerror(i, line, f'Not enough arguments for {op} operation (expected 1 register, got {len(args)} args)')
                return None
            reg = args[0]
            if len(reg) > 1:
                printerror(i, line, f'Invalid register specifier "{reg}"')
                return None
            try:
                reg = int(reg, 16)
            except ValueError:
                printerror(i, line, f'Invalid register specifier "{reg}"')
                return None
            instructions.append((op_num, reg))

        # Handle operations with two register arguments (ADD, AND, MV, NOT, RS, LS, SW)
        if op_num in two_reg_ops:
            if len(args) > 2:
                printerror(i, line, f'Too many arguments for {op} operation (expected 2 registers, got {len(args)} args)')
                return None
            if len(args) < 2:
                printerror(i, line, f'Not enough arguments for {op} operation (expected 2 registers, got {len(args)} args)')
                return None
            reg1, reg2 = args
            if len(reg1) > 1:
                printerror(i, line, f'Invalid register specifier - "{reg1}"')
                return None
            try:
                reg1 = int(reg1, 16)
            except ValueError:
                printerror(i, line, f'Invalid register specifier - "{reg1}"')
                return None
            if len(reg2) > 1:
                printerror(i, line, f'Invalid register specifier - "{reg2}"')
                return None
            try:
                reg2 = int(reg2, 16)
            except ValueError:
                printerror(i, line, f'Invalid register specifier - "{reg2}"')
                return None
            instructions.append((op_num, reg1, reg2))

    # Second pass: resolve label references in instructions
    # Replace label name with instruction index
    for j, (op, *args) in enumerate(instructions):
        if op in label_ops:
            lbl = args[0]
            # Check that a referenced label was previously defined
            if lbl not in label_map:
                i, line = lbl_lines[j]
                printerror(i, line, f'Undefined label reference - "{lbl}"')
                return None
            # Update the instruction with the resolved instruction index
            instructions[j] = (op, label_map[lbl])

    # Return the assembled program as a tuple of instructions, register initializations, and memory initializations
    return instructions, reg_inits, mem_inits
