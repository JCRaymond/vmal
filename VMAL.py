import VMALAssembler
from pprint import pprint

int32_max = 0xffffffff

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
   code, regstate, memstate = code
   
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
               return state, mem
            else:
               print('Invalid operation, please try again')
               continue
            break
      runop(*op)
      state[0] += 1
   return state, mem

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
   else:
      fname = argv[1]
   
   print('Compiling...')
   with open(fname, 'r') as codefile:
      machine_code = VMALAssembler.assemble(codefile)
   if machine_code is None:
      print('Failed to complie, terminating')
      return
   print('Compiled!')
   
   resp = input('Press ENTER to run the program, or type "d" or "debug" to run the program in debug mode: ')
   
   if len(resp) == 0 or resp[0].lower() != 'd':
      finalstate, mem = runcode(machine_code)
   else:
      print()
      print('Assembled Code:')
      for i, op in enumerate(machine_code[0]):
         print(i, ': ', sep='', end='')
         printop(op)
      finalstate, mem = runcode(machine_code, debug = True)
   
   print()
   print('Final Register State:')
   printregisters(finalstate)
   print()
   for k in mem:
      v = mem[k]
      mem[k] = v if v & 0x80000000 == 0 else -((-v) & int32_max)
   pprint(mem)
   
if __name__ == "__main__":
   try:
      main()
   except Exception as err:
      print(err)
      print('ERROR OCCURED')
   input('Press ENTER to terminate...')
