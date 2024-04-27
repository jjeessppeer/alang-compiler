
import sys

# Usage:
# python3 assembler.py [input_file] [output_file]
# Example: python3 assembler.py test.asm out.txt
#
# Aseembly sytax:
# [instruction] [register idx] [address mode] [data]
# Example: 
# LOAD 0 DIR 15
# LOAD 0 DIR 0xF
# LOAD 0 DIR 0b1111

INSTRUCTION_MAP = {
    "NOP"   : 0,
    "LOAD"  : 1,
    "STORE" : 2,
    "JMP"   : 3,
    "ADD"   : 4,
    "SUB"   : 5,
    "MUL"   : 6,
    "JNE"   : 7,
    "CMP"   : 8,
    "AND"   : 9,
    "OR"    : 10,
    "HALT"  : 11,
    "CALL"  : 12,
    "RET"   : 13,
    "PUSH"  : 14,
    "POP"   : 15,
    "LSR"   : 16,
    "LSL"   : 17,
    "JGR"   : 18
}

ADDRESS_MODES = {
    "DIR": 0,
    "IM": 1,
    "IND": 2,
    "IDX": 3,
    "REG" : 4
}

class AssemblerException(Exception): pass

def assemble(text):
    lines = text.splitlines()
    machinecode = []
    for idx, l in enumerate(lines):
        try:
            instruction = asm_to_machinecode(l)
        except AssemblerException as e:
            print(f"Assembler failed. {e} On row {idx}, \"{l}\"")
            exit()
        machinecode.append(instruction)
    return "\n".join(machinecode)

def asm_to_machinecode(line):
    """Convert a line of assembly code to binary machine code instruction."""
    line = line.replace("\t", " ")
    words = line.strip().split(" ")

    # Parse operation
    try:
        instr = INSTRUCTION_MAP[words[0].upper()]
    except:
        raise AssemblerException("Invalid instruction used.")
    
    # Parse GrX.
    gr = 0
    if (len(words) >= 2):
        try:
            gr = int(words[1], 0)
        except:
            raise AssemblerException("Invalid register index value.")
        if (gr > 0b11111): 
            raise AssemblerException("Invalid register index value.")
        
    # Parse address mode.
    m = 0
    if (len(words) >= 3):
        if words[3] in ADDRESS_MODES:
            m = ADDRESS_MODES[words[3]]
        else:
            try:
                m = int(words[2], 0)
            except:
                raise AssemblerException("Invalid address mode value.")
        if (m > 0b100): 
            raise AssemblerException("Invalid address mode value.")
        
    # Parse data.
    data = 0
    if (len(words) >= 4):
        try:
            data = int(words[3], 0)
        except:
            raise AssemblerException("Invalid data value.")
        if data > 0xFFFFF:
            raise AssemblerException("Invalid data value.")
    
    return f"{instr:05b}{gr:05b}{m:03b}{data:020b}"