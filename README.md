# VMAL
This repository holds the reference implementation for VMAL, an assembly language for the Vertical Microarchitecture discussed in ITSC 3181 at UNC-Charlotte.

## Requirements
All of the code for VMAL is contained within VMAL.py, which requires Python 3.5 or greater (tested on 3.5 and later, it might work on earlier versions of python) as well as the package `lark-parser` which can be installed with pip:
```bash
pip install --user lark-parser
```

## Running VMAL
In order to run VMAL, there are two options. The first is to just run VMAL with python, i.e.
```bash
python VMAL.py
```
Which will open a file browser to select the .vmal file to execute, or you may pass the file directly as a command line argument, which will supress the file browser prompt
```bash
python VMAL.py my_code.vmal
```
