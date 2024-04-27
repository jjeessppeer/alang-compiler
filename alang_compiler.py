from alang_parser import parse_file, Statement, IfStatement
from compiler_utils import (
    parse_function, 
    parse_variable, 
    deref_variable,
    get_block,
    instructions_to_string,
    Instruction, 
    JmpBackPlaceholder, 
    JmpToPlaceholder, 
    CompilationError
)
import json
import re

# https://regex-vis.com/
return_rgx = r"return( (([*&])?(\w+)))?$"
if_rgx = r"(if|while)\(([\w*&]+)(!=|<|>)([\w*&]+)\)$"
halt_rgx = r"(halt)$"

OP_MAP = {
    "+": "ADD",
    "-": "SUB",
    "*": "MUL",
    "=": "STORE"
}

def compile_func_call(fn_name, fn_params, block, all_blocks):
    """Compile a function call to assembly instructions."""
    func_map = block["functions"]
    if fn_name not in func_map:
        raise CompilationError(f"Undeclared function used: {fn_name}")
    func_code = func_map[fn_name]

    instructions = []
    instructions.append(Instruction("PUSH", 0)) # Stash GR0

    # Set function parameter variables
    target_block = get_block(func_code, all_blocks)
    for idx, param in enumerate(fn_params):
        if idx >= len(target_block["parameters"]):
            raise CompilationError("Too many parameter values given.")
        
        # Load the local variable
        adr_op, var_name, _ = parse_variable(param, True)
        m, val = deref_variable(adr_op, var_name, block["variables"])
        instructions.append(Instruction("LOAD", 0, m, val)) 

        # Store in the target variable
        _, val = deref_variable(None, target_block["parameters"][idx], target_block["variables"])
        instructions.append(Instruction("STORE", 0, 0, val)) # Store in function variable
        
    instructions.append(JmpToPlaceholder("CALL", func_code, 0))
    instructions.append(Instruction("POP", 0)) # Retrieve stashed GR1
    return instructions

def compile_expression(expression, block, all_blocks):
    """Compile an expression (x+y-z...) to assembly instructions."""
    instructions = []
    # Load first operand
    if f := parse_function(expression):
        fn_name, fn_params, width = f
        instructions += compile_func_call(fn_name, fn_params, block, all_blocks)
        instructions.append(Instruction("LOAD", 0, 4, 1)) # Functions store their return value in GR1
        i = width
    elif v := parse_variable(expression):
        adr_op, var_name, width = v
        m, val = deref_variable(adr_op, var_name, block["variables"])
        instructions.append(Instruction("LOAD", 0, m, val))
        i = width
    else:
        raise CompilationError("Invalid syntax.")

    while i < len(expression):
        operand = expression[i]
        op = OP_MAP[operand]
        if f := parse_function(expression[i+1:]):
            fn_name, fn_params, width = f
            instructions += compile_func_call(fn_name, fn_params, block, all_blocks)
            instructions.append(Instruction(op, 0, 5, 1)) # Functions store their return value in GR1
            i += width + 1
        elif v := parse_variable(expression[i+1:]):
            adr_op, var_name, width = v
            m, val = deref_variable(adr_op, var_name, block["variables"])
            instructions.append(Instruction(op, 0, m, val))
            i += width + 1
        else:
            raise CompilationError("Invalid syntax.")
    return instructions

def compile_assignment(assign_target, block):
    """Compile a value assignment (x=) to assembly instructions."""
    adr_op, var_name, _ = parse_variable(assign_target, True)
    m, val = deref_variable(adr_op, var_name, block["variables"])
    if m != 0 and m != 2 and m != 3:
        raise CompilationError(f"Invalid address mode for assignment {assign_target}")
    
    return [
        Instruction("STORE", 0, m, val) # Store GR0 to the specified variable.
    ]

def compile_statement(statement, block, all_blocks):
    """Compile a single statment to assembly instructions."""
    instructions = []
    if isinstance(statement, IfStatement):
        s = statement.text.replace(" ", "")
        r = re.match(if_rgx, s)
        if not r:
            raise CompilationError("Invalid if statement")
        operand = r.group(3)

        adr_op_1, var_name_1, _ = parse_variable(r.group(2), True)
        adr_op_2, var_name_2, _ = parse_variable(r.group(4), True)
        m_1, val_1 = deref_variable(adr_op_1, var_name_1, block["variables"])
        m_2, val_2 = deref_variable(adr_op_2, var_name_2, block["variables"])

        if operand == "!=":
            instructions.append(Instruction("LOAD", 0, m_1, val_1))
            instructions.append(Instruction("CMP", 0, m_2, val_2))
            instructions.append(JmpToPlaceholder("JNE", statement.target_block, 0))
        elif operand == "<":
            instructions.append(Instruction("LOAD", 0, m_1, val_1))
            instructions.append(Instruction("CMP", 0, m_2, val_2))
            instructions.append(JmpToPlaceholder("JGR", statement.target_block, 0))
        elif operand == ">":
            instructions.append(Instruction("LOAD", 0, m_2, val_2))
            instructions.append(Instruction("CMP", 0, m_1, val_1))
            instructions.append(JmpToPlaceholder("JGR", statement.target_block, 0))
        # elif operand == "==":
        #     instructions.append(Instruction("LOAD", 0, m_1, val_1))
        #     instructions.append(Instruction("CMP", 0, m_2, val_2))
        #     instructions.append(JmpToPlaceholder("JEQ", statement.target_block, 0))
        
    elif r := re.match(return_rgx, statement.text):
        # Compile function return statement.
        if r.group(2):
            adr_op, var_name, _ = parse_variable(r.group(2), True)
            m, val = deref_variable(adr_op, var_name, block["variables"])
            instructions.append(Instruction("LOAD", 1, m, val)) # Store return value in GR1
        instructions.append(Instruction("RET"))
    elif r := re.match(halt_rgx, statement.text):
        instructions.append(Instruction("HALT"))
    else: 
        # Compile assignment and expression statement.
        # TODO: add regex match.
        s = statement.text.replace(" ", "") # Trim spaces.
        lhs, eq, rhs = s.partition("=")
        if not eq:
            rhs = lhs
            lhs = None
        instructions += compile_expression(rhs, block, all_blocks)
        if lhs:
            instructions += compile_assignment(lhs, block)
    
    return instructions

def compile_block(block, all_blocks):
    """Compile a code block to a list of assembly instructions."""
    # print(f"\nCompiling block {block['block_type']} {block['name']}")
    instructions = []
    comments = {}
    for statement in block["code"]:
        comments[len(instructions)] = statement.text
        try:
            instructions += compile_statement(statement, block, all_blocks)
        except Exception as e:
            print(f"Compilation failed at line {statement.row} \"{statement.text}\"\n{e}")
            exit()

    if block["block_type"] == "function":
        # Always return at the end of functions.
        comments[len(instructions)] = "implicit return"
        instructions.append(Instruction("RET"))
    elif block["block_type"] == "if" or block["block_type"] == "while":
        # Jump back to previous function.
        comments[len(instructions)] = "jump back"
        instructions.append(JmpBackPlaceholder())
        pass
    return instructions, comments

def insert_jumps(instructions, blocks):
    for idx, inst in enumerate(instructions):
        if isinstance(inst, JmpToPlaceholder):
            target_block = get_block(inst.block_id, blocks)
            target_addr = target_block["start_address"] + inst.offset

            # Find matching jump back instruction for if and while.
            if target_block["block_type"] == "if":
                instructions[target_block["end_address"]] = Instruction("JMP", 0, 1, idx + 1)
            elif target_block["block_type"] == "while":
                instructions[target_block["end_address"]] = Instruction("JMP", 0, 1, idx - 2)
            instructions[idx] = Instruction(inst.op, 0, 1, target_addr)

def compile_alang(code_blocks):
    program_instructions = []
    p_comments = {}
    for block in code_blocks:
        block_instructions, comments = compile_block(block, code_blocks)

        # Add instructions to the program.
        start_adr = len(program_instructions)
        block["start_address"] = start_adr
        block["end_address"] = start_adr + len(block_instructions) - 1
        program_instructions += block_instructions

        # Merge in comments
        if 0 in comments:
            comments[0] += f" | {block['block_type']} {block['name']}"
        for idx, comment in comments.items():
            p_comments[start_adr+idx] = comment
    
    # print(instructions_to_string(program_instructions, p_comments))
    insert_jumps(program_instructions, code_blocks)
    # print(instructions_to_string(program_instructions, p_comments))

    # return program_instructions, p_comments
    return instructions_to_string(program_instructions, p_comments)

if __name__ == "__main__":
    code_blocks = parse_file("test1.alang")
    try:
        compiled = compile_alang(code_blocks)
    except CompilationError as e:
        print(e)
    # print(json.dumps(compiled, indent=2))