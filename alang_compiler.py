from alang_parser import parse_file
import json

class CompilationError(Exception): pass

MATH_INSTRUCTIONS = {
    "+": "ADD",
    "-": "SUB",
    "*": "MUL"
}

def deref_val(var_name, block):
    """Return value and address mode for variable access."""
    try:
        # Constant
        val = int(var_name, 0)
        return 1, val
    except: pass

    m = 0
    if var_name[0] == "&":
        m = 1
        var_name = var_name[1:]
    elif var_name[0] == "*":
        m = 2
        var_name = var_name[1:]
    # elif
    # m = 3
    # TODO: indexed.
    if var_name not in block["variables"]:
        raise CompilationError(f"Compilation failed. Undeclared variable used: {var_name}")

    return m, block["variables"][var_name]

def operation_to_assembly(operation, block):
    op_type = operation["type"]
    instructions = []
    
    if op_type == "assign_copy":
        m, dat = deref_val(operation["source"], block)
        instructions.append({
            "op": "LOAD",
            "m": m,
            "grx": 0,
            "data": dat
        })
        m, dat = deref_val(operation["target"], block)
        instructions.append({
            "op": "STORE",
            "m": m,
            "grx": 0,
            "data": dat
        })

    elif op_type == "assign_math":
        m, dat = deref_val(operation["source"][0], block)
        instructions.append({
            "op": "LOAD",
            "m": m,
            "grx": 0,
            "data": dat
        })
        m, dat = deref_val(operation["source"][1], block)
        instructions.append({
            "op": MATH_INSTRUCTIONS[operation["operand"]],
            "m": m,
            "grx": 0,
            "data": dat
        })
        m, dat = deref_val(operation["target"], block)
        instructions.append({
            "op": "STORE",
            "m": m,
            "grx": 0,
            "data": dat
        })

    else:
        print(operation)
        instructions.append("UNKNOWN")
    return instructions

def compile_block(block):
    """Compile a code block to assembly instructions."""
    assembly_instructions = []
    for operation in block["code"]:
        instr = operation_to_assembly(operation, block)
        assembly_instructions += instr
    return assembly_instructions
        
def place_functions():
    pass

def compile_alang(code_blocks):
    # Compilation process.
    # 1. Compile all code blocks to assembly. 
    #    Insert temporary instructions in place of JMP, CALL. 
    #    Code block memory positions is still unknown.
    # 2. Get memory length of each code block.
    # 3. Place functions in memory space.
    # 4. Fill in function references.

    for block in code_blocks:
        ass = compile_block(block)

        print(json.dumps(ass, indent=2))

    return code_blocks

if __name__ == "__main__":
    code_blocks = parse_file("test1.alang")
    try:
        compiled = compile_alang(code_blocks)
    except CompilationError as e:
        print(e)
    # print(json.dumps(compiled, indent=2))