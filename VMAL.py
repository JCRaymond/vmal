import vmal.VMALAssembler
from collections import defaultdict
from pprint import pprint

ops = ['SA', 'RB', 'RD', 'WR', 'SB', 'SF', 'GO', 'BIN', 'BIZ', 'ADD', 'AND', 'MV', 'NOT', 'RS', 'LS', 'SW']
def op_str(op):
   op, *params = op
   if op == 6 or op == 7 or op == 8:
      params[0] += 1
      params = map(str, params)
   else:
      params = map(lambda p: str(hex(p))[2:].upper(), params)
   return f'{ops[op]} {", ".join(params)}'

def printcode(code):
   print(*(f'{i: 3}: {op_str(op)}' for i, op in enumerate(code)), sep = '\n')

def get_int(reg_val):
   return (reg_val if reg_val & 0x80000000 == 0 else -((-reg_val) & VM.int_max))

class VM:
   int_max = 0xffffffff

   def __init__(self, reg_inits=[], mem_inits=[]):
      self.registers = [0]*16
      for reg, val in reg_inits:
         self.registers[reg] = val & VM.int_max
         
      self.registers[0] = 0
      self.registers[5] = 0
      self.registers[6] = 1
      self.registers[7] = VM.int_max

      self.memory = defaultdict(lambda: 0)
      for loc, val in mem_inits:
         self.memory[loc] = val & VM.int_max

      self.MAR = 0
      self.MBR = 0
      self.N = False
      self.Z = False

   def setreg(self, reg, val):
      self.registers[reg] = val & VM.int_max

   def setmem(self, loc, val):
      self.memory[loc] = val

   def printregisters(self):
      print()
      print('Registers:')
      for i, v in enumerate(self.registers):
         print(f'{str(hex(i))[2:].upper()}: {get_int(v)}')
      print()

   def printmemory(self):
      print()
      print('Memory:')
      items = iter(sorted(self.memory.items()))
      loc, v = next(items)
      print(f'[{loc}]: {get_int(v)}')
      last = loc
      for loc, v in items:
         if loc - last > 1:
            print(f'... {loc - last - 1} empty locations ...')
         print(f'[{loc}]: {get_int(v)}')
         last = loc
      print()

   def SA(self, X):
      self.MAR = self.registers[X]
   def RB(self, X):
      self.registers[X] = self.MBR
   def RD(self):
      self.MBR = 0
      if self.MAR in self.memory:
         self.MBR = self.memory[self.MAR]
   def WR(self):
      self.memory[self.MAR] = self.MBR
   def SB(self, X):
      self.MBR = self.registers[X]
   def SF(self, X):
      self.Z = (self.registers[X] == 0)
      self.N = bool(self.registers[X] & 0x80000000)
   def GO(self, I):
      self.registers[0] = I
   def BIN(self, I):
      if self.N:
         self.registers[0] = I
   def BIZ(self, I):
      if self.Z:
         self.registers[0] = I
   def ADD(self, X, Y):
      self.registers[X] = (self.registers[X] + self.registers[Y]) & VM.int_max
   def AND(self, X, Y):
      self.registers[X] = (self.registers[X] & self.registers[Y]) & VM.int_max
   def MV(self, X, Y):
      self.registers[X] = self.registers[Y]
   def NOT(self, X, Y):
      self.registers[X] = (~self.registers[Y]) & VM.int_max
   def RS(self, X, Y):
      self.registers[X] = (self.registers[Y] >> 1) & VM.int_max
   def LS(self, X, Y):
      self.registers[X] = (self.registers[Y] << 1) & VM.int_max
   def SW(self, X, Y):
      self.MAR = self.registers[X]
      self.MBR = self.registers[Y]
      self.memory[self.MAR] = self.MBR

   ops = [SA, RB, RD, WR, SB, SF, GO, BIN, BIZ, ADD, AND, MV, NOT, RS, LS, SW]

   def runop(self, op, *params):
      self.ops[op](self, *params)

   def runcode(self, code, *, limit = float('inf')):
      i = 0
      while self.registers[0] < len(code):
         if i >= limit:
            return False
         op = code[self.registers[0]]
         self.runop(*op)
         self.registers[0] += 1
         i += 1
      return True

   def rundebug(self, code, *, limit = float('inf')):
      i = 0
      bp = set()
      cont = False
      while self.registers[0] < len(code):
         if i >= limit:
            return False
         op = code[self.registers[0]]
         on_bp = self.registers[0] in bp
         if not cont or on_bp:
            self.printregisters()
            
            print('Flags:')
            print('N:', self.N)
            print('Z:', self.Z)
            
            print()
            if cont:
               print('Continue till Breakpoint')
            if on_bp:
               print('BREAKPOINT')
            print(f'Operation: {op_str(op)}',end='')
            
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
                  if self.registers[0] in bp:
                     bp.remove(self.registers[0])
                     print('OFF')
                  else:
                     bp.add(self.registers[0])
                     print('ON')
                  continue
               elif resp == 'c':
                  cont = not cont
               elif resp == 'r':
                  debug = False
               elif resp == 'q':
                  return False
               else:
                  print('Invalid operation, please try again')
                  continue
               break
         self.runop(*op)
         self.registers[0] += 1
         i += 1
      return True

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
   
   print('Assembling...')
   with open(fname, 'r') as codefile:
      machine_code = VMALAssembler.assemble(codefile)
   if machine_code is None:
      print('Failed to assemble, terminating')
      return
   print('Assembled!')

   code, reg_inits, mem_inits = machine_code
   vm = VM(reg_inits, mem_inits)
   
   resp = input('Press ENTER to run the program, or type "d" or "debug" to run the program in debug mode: ')
   
   if len(resp) == 0 or resp[0].lower() != 'd':
      success = vm.runcode(code)
   else:
      print()
      print('Assembled Code:')
      for i, op in enumerate(machine_code[0]):
         print(i, ': ', sep='', end='')
         printop(op)
      success = vm.rundebug(machine_code)

   if not success:
      print('Code run was not successful (operation limit reached or program quit), terminating')
      return
   
   vm.printregisters()

   if len(vm.memory) > 0:
      vm.printmemory()
   
   
if __name__ == "__main__":
   try:
      main()
   except Exception as err:
      print(err)
      print('ERROR OCCURED')
   input('Press ENTER to terminate...')
