import re

op_map = {
   'SA': 0,
   'RB': 1,
   'RD': 2,
   'WR': 3,
   'SB': 4,
   'SF': 5,
   'LBL': -1,
   'GO': 6,
   'BIN': 7,
   'BIZ': 8,
   'ADD': 9,
   'AND': 10,
   'MV': 11,
   'NOT': 12,
   'RS': 13,
   'LS': 14,
   'SW': 15
}

label_ops = {-1, 6, 7, 8}
zero_arg_ops = {2, 3}
one_reg_ops = {0, 1, 4, 5}
two_reg_ops = {9, 10, 11, 12, 13, 14, 15}

def printerror(i, line, msg):
    print(f'Error on line #{i+1}: {msg}')
    print(f'\t> {line}')

def parse_number(s):
    if s[:2] == '0x':
        try:
            return int(s[2:], 16), None
        except ValueError:
            return None, 'Invalid hexadecimal literal in {} initializer - "{}"'
    if s[:2] == '0b':
        try:
            return int(s[2:], 2), None
        except ValueError:
            return None, 'Invalid binary literal in {} initializer - "{}"'
    try:
        return int(s), None
    except ValueError:
        return None, 'Invalid character sequence in {} initializer - "{}"'

is_cname = re.compile('[_a-zA-Z][_a-zA-Z0-9]*')

def assemble(f):
    reg_inits = []
    mem_inits = []
    instructions = []
    lbl_lines = {}
    label_map = {}
    for i, line in enumerate(f):
        code, _, comment = line.partition('#')
        del comment
        code = code.strip()
        if not code:
            continue
        code, semicol, rest = code.partition(';')
        if semicol != ';':
            printerror(i, line, 'Missing semicolon')
            return None
        rest = rest.strip()
        if rest:
            printerror(i, line, f'Extra non-comment character sequence after semicolon - "{rest}"')
            return None
        bpart, col, epart = code.partition(':')
        if col == ':':
            loc = bpart.strip()
            val = epart.strip()
            is_reg_init = False
            msg = ''
            if len(loc) == 1:
                try:
                    reg = int(loc, 16)
                except ValueError:
                    printerror(i, line, f'Invalid register in register initializer - "{loc}"')
                    return None
                is_reg_init = True
                msg = 'register'
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
            val, err = parse_number(val)
            if val is None:
                printerror(i, line, err.format(msg, val))
                return None
            if is_reg_init:
                reg_inits.append((reg, val))
            else:
                mem_inits.append((mem, val))
            continue
        op, space, args = code.strip().partition(' ')
        op = op.upper()
        if op != 'RD' and op != 'WR' and space != ' ':
            printerror(i, line, f'Unknown character sequence "{op}"')
            return None
        if op not in op_map:
            printerror(i, line, f'Unknown operation "{op}"')
            return None
        op_num = op_map[op]
        args = [arg.strip() for arg in args.split(',') if len(arg.strip()) > 0]
        if op_num in label_ops:
            if len(args) > 1:
                printerror(i, line, f'Too many arguments for {op} operation (expected 1 label, got {len(args)} args)')
                return None
            if len(args) < 1:
                printerror(i, line, f'Not enough arguments for {op} operation (expected 1 label, got {len(args)} args)')
                return None
            lbl = args[0]
            if op_num == -1:
                match = is_cname.fullmatch(lbl)
                if match is None:
                    printerror(i, line, f'Label name is not a valid cname - "{lbl}"')
                    return None
                if lbl in label_map:
                    printerror(i, line, f'Label "{lbl}" already defined')
                    return None
                label_map[lbl] = len(instructions) - 1
                continue
            lbl_lines[len(instructions)] = (i, line)
            instructions.append((op_num, lbl))
            continue
        if op_num in zero_arg_ops:
            if len(args) > 0:
                printerror(i, line, f'Too many arguments for {op} operation (expected no arguments, got {len(args)} args)')
                return None
            instructions.append((op_num,))
            continue
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

    for j, (op, *args) in enumerate(instructions):
        if op in label_ops:
            lbl = args[0]
            if lbl not in label_map:
                i, line = lbl_lines[j]
                printerror(i, line, f'Undefined label reference - "{lbl}"')
                return None
            instructions[j] = (op, label_map[lbl])

    return instructions, reg_inits, mem_inits
