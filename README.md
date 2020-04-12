# VMAL
This repository holds the reference implementation for VMAL, an assembly language for the Vertical Microarchitecture discussed in ITSC 3181 at UNC-Charlotte.

## Requirements
The main file to run is VMAL.py (which uses VMALAssembler.py), which requires Python 3.6 or greater. Optionally, if you wish to use the file explorer to select the code to run, the `easygui` package is required, which can be installed with pip:
```bash
pip install --user easygui
```

## Running VMAL
In order to run VMAL, there are two options. The first is to just run VMAL with python, i.e.
```bash
python3.6 VMAL.py
```
Which will open a file browser to select the .vmal file to execute (this requires `easygui`). Alternatively, you may pass the file directly as a command line argument, which will supress the file browser prompt (and does not require the `easygui` package).
```bash
python3.6 VMAL.py my_code.vmal
```
