from lark import Lark, Transformer, v_args

opmap = {
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

label_ops = {-1,6,7,8}

int32_max = 0xffffffff

class Assembler(Transformer):
   @v_args(inline=True)
   def start(self, regstate, memstate, code):
      return {'regstate':regstate, 'memstate':memstate, 'code':code}

   def code(self, ops):
      labels = {}
      i = 0
      while i < len(ops):
         op = ops[i]
         if op[0] == -1:
            labels[op[1]] = i
            del ops[i]
         else:
            i+=1
      for i,op in enumerate(ops):
         if op[0] in label_ops:
            ops[i] = (op[0], labels[op[1]] - 1)
      return ops

   @v_args(inline=True)
   def opname(self, opname):
      return opmap[opname.upper()]
   @v_args(inline=True)
   def param(self, param):
      return param
   @v_args(inline=True)
   def operation(self, op, *params):
      if op not in label_ops:
         params = list(map(lambda p: int(p, 16), params))
      else:
         params = list(map(str,params))
      return (op, *params)
   
   def regstate(self, reginits):
      return reginits
   def memstate(self, meminits):
      return meminits
   @v_args(inline=True)
   def decnum(self, num):
      return int(num) & int32_max
   @v_args(inline=True)
   def hexnum(self, num):
      return int(num, 16) & int32_max
   @v_args(inline=True)
   def binnum(self, num):
      return int(num, 2) & int32_max
   @v_args(inline=True)
   def register(self, regnum):
      return int(regnum, 16)
   @v_args(inline=True)
   def memloc(self, memloc):
      return memloc
   @v_args(inline=True)
   def reginit(self, register, num):
      return (register, num)
   @v_args(inline=True)
   def meminit(self, memloc, num):
      return (memloc, num)

grammar = """
start: regstate memstate code

// Lexers

HEXNUM: /[0-9a-fA-F]+/
BINNUM: /[01]+/
BINDIGIT: /[01]/
PARAM: /[0-9a-zA-Z_]+/
COMMENT: /#[^\\n]*/

// START COMMON.LARK

DIGIT: "0".."9"
HEXDIGIT: "a".."f"|"A".."F"|DIGIT
INT: DIGIT+
SIGNED_INT: ["+"|"-"] INT
LCASE_LETTER: "a".."z"
UCASE_LETTER: "A".."Z"
LETTER: UCASE_LETTER | LCASE_LETTER
CNAME: ("_"|LETTER) ("_"|LETTER|DIGIT)*
WS_INLINE: (" "|/\\t/)+
WS: /[ \\t\\f\\r\\n]+/

// END COMMON.LARK

// 'Tokens'

opname: CNAME
param: PARAM

register: HEXDIGIT
memloc: "[" _number "]"
hexnum: "0x" HEXNUM
binnum: "0b" BINNUM
decnum: SIGNED_INT 

// Parse register initializers

regstate: reginit*
memstate: meminit*

reginit: register ":" _number ";"
meminit: memloc ":" _number ";"

_number: hexnum | binnum | decnum

// Parse assembly

code: operation*

_paramlist: param | param "," _paramlist
_params: param? | _paramlist

operation: opname _params ";"

// Ignores

%ignore WS
%ignore WS_INLINE
%ignore COMMENT
"""

def printregisters(arr):
    print(*(str(hex(i))[2:].upper() + ': ' + str(v if v & 0x80000000 == 0 else -((-v) & int32_max)) for i,v in enumerate(arr)), sep='\n')

ops = ['SA', 'RB', 'RD', 'WR', 'SB', 'SF', 'GO', 'BIN', 'BIZ', 'ADD', 'AND', 'MV', 'NOT', 'RS', 'LS', 'SW']
def printop(op):
   op, *params = op
   if op == 6 or op == 7 or op == 8:
      params[0] += 1
      params = map(str, params)
   else:
      params = map(lambda p: str(hex(p))[2:].upper(), params)
   print(ops[op], ', '.join(params))

def runcode(code, debug=False):
   regstate = code['regstate']
   memstate = code['memstate']
   code = code['code']
   
   state = [0] * 16
   for reg, val in regstate:
      state[reg] = val & int32_max
   state[5] = 0
   state[6] = 1
   state[7] = int32_max

   mem = {}
   for loc, val in memstate:
      mem[loc] = val

   MAR = 0
   MBR = 0
   N = False
   Z = False

   def SA(X):
      nonlocal MAR
      MAR = state[X]
   def RB(X):
      state[X] = MBR
   def RD():
      nonlocal MBR
      MBR = 0
      if MAR in mem:
         MBR = mem[MAR]
   def WR():
      mem[MAR] = MBR
   def SB(X):
      nonlocal MBR
      MBR = state[X]
   def SF(X):
      nonlocal Z, N
      Z = (state[X] == 0)
      N = bool(state[X] & 0x80000000)
   def GO(I):
      state[0] = I
   def BIN(I):
      if N:
         state[0] = I
   def BIZ(I):
      if Z:
         state[0] = I
   def ADD(X,Y):
      state[X] = (state[X] + state[Y]) & int32_max
   def AND(X,Y):
      state[X] = (state[X] & state[Y]) & int32_max
   def MV(X,Y):
      state[X] = state[Y]
   def NOT(X,Y):
      state[X] = (~state[Y]) & int32_max
   def RS(X,Y):
      state[X] = (state[Y] >> 1) & int32_max
   def LS(X,Y):
      state[X] = (state[Y] << 1) & int32_max
   def SW(X,Y):
      nonlocal MAR, MBR
      MAR = state[X]
      MBR = state[Y]
      mem[MAR] = MBR

   ops = [SA, RB, RD, WR, SB, SF, GO, BIN, BIZ, ADD, AND, MV, NOT, RS, LS, SW]

   def runop(op, *params):
      ops[op](*params)

   state[0] = 0
   bp = set()
   quit = False
   cont = False
   while state[0] < len(code) and not quit:
      op = code[state[0]]
      on_bp = state[0] in bp
      if debug and (not cont or on_bp):
         print()
         print('Registers:')
         printregisters(state)
         
         print()
         print('Flags:')
         print('N:', N)
         print('Z:', Z)
         
         print()
         if cont:
            print('Continue till Breakpoint')
         if on_bp:
            print('BREAKPOINT')
         print('Operation: ',end='')
         printop(op)
         
         while True:
            resp = input('Debug (n,b,c,r,q): ')
            if len(resp) == 0:
               resp = 'n'
            else:
               resp = resp[0].lower()
            if resp == 'n':
               pass
            elif resp == 'b':
               print('Turning Breakpoint ', end='')
               if state[0] in bp:
                  bp.remove(state[0])
                  print('OFF')
               else:
                  bp.add(state[0])
                  print('ON')
               continue
            elif resp == 'c':
               cont = not cont
            elif resp == 'r':
               debug = False
            elif resp == 'q':
               return state
            else:
               print('Invalid operation, please try again')
               continue
            break
      runop(*op)
      state[0] += 1
   return state

def main():
   from sys import argv, executable
   from os.path import dirname, abspath, exists, join
   
   if len(argv) < 2:
      from easygui import fileopenbox
      
      execpath = dirname(abspath(executable))
      lf = join(execpath, '.lastfolder')
      
      defpath = '*.vmal'
      if exists(lf):
         with open(lf, 'r') as f:
            defpath = join(f.read().strip(), defpath)
      
      fname = fileopenbox('Select the .vmal file to run', 'VMAL File Selector', default=defpath)
      
      if fname is None:
         print('No file selected, terminating')
         return
      
      ffolder = dirname(abspath(fname))
      with open(lf, 'w') as f:
         f.write(ffolder)
      
      code = open(fname,'r').read()
   else:
      code = open(argv[1],'r').read()
   
   print('Compiling...')
   parser = Lark(grammar)
   machine_code = Assembler().transform(parser.parse(code))
   print('Compiled!')
   
   resp = input('Press ENTER to run the program, or type "d" or "debug" to run the program in debug mode: ')
   
   if len(resp) == 0 or resp[0].lower() != 'd':
      finalstate = runcode(machine_code)
   else:
      print()
      print('Assembled Code:')
      for i, op in enumerate(machine_code['code']):
         print(i, ': ', sep='', end='')
         printop(op)
      finalstate = runcode(machine_code, debug = True)
   
   print()
   print('Final Register State:')
   printregisters(finalstate)
   print()
   
if __name__ == "__main__":
   try:
      main()
   except Exception as err:
      print(err)
      print('ERROR OCCURED')
   input('Press ENTER to terminate...')
