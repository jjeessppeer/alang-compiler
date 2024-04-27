from alang_parser import parse_file, Statement, IfStatement
from compiler_utils import (
    parse_function, 
    parse_variable, 
    deref_variable,
    get_block,
    CallPlaceholder, 
    Instruction, 
    JmpBackPlaceholder, 
    JmpToPlaceholder, 
    CompilationError
)
import json
import re

# https://regex-vis.com/
return_rgx = r"return( (([*&])?(\w+)))?"
if_rgx = r"(if|while)\(([\w*&]+)(!=|<|>)([\w*&]+)\)"

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
        # Load the local variable
        adr_op, var_name, _ = parse_variable(param, True)
        m, val = deref_variable(adr_op, var_name, block["variables"])
        instructions.append(Instruction("LOAD", 0, m, val)) 

        # Store in the target variable
        _, val = deref_variable(None, target_block["parameters"][idx], target_block["variables"])
        instructions.append(Instruction("STORE", 0, 0, val)) # Store in function variable
        
    instructions.append(CallPlaceholder(func_code))
    instructions.append(Instruction("POP", 0)) # Retrieve stashed GR1
    return instructions

def compile_expression(expression, block, all_blocks):
    """Compile an expression (x+y-z...) to assembly instructions."""
    instructions = []
    # Load first operand
    if f := parse_function(expression):
        fn_name, fn_params, width = f
        instructions += compile_func_call(fn_name, fn_params, block, all_blocks)
        instructions.append(Instruction("LOAD", 0, 5, 1)) # Functions store their return value in GR1
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

def compile_block(block, all_blocks):
    """Compile a code block to a list of assembly instructions."""
    print(f"\nCompiling block {block['block_type']} {block['name']}")
    instructions = []
    comments = {}
    for statement in block["code"]:
        comments[len(instructions)] = statement.text
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

    if block["block_type"] == "function":
        # Always return at the end of functions.
        comments[len(instructions)] = "default return"
        instructions.append(Instruction("RET"))
        # assembly_instructions.append()
    elif block["block_type"] == "if":
        # Jump back to previous function.
        instructions.append(JmpBackPlaceholder())
        pass
    return instructions, comments
    
def compile_alang(code_blocks):
    # Compilation process.
    # 1. Compile all code blocks to assembly. 
    #    Insert temporary instructions in place of JMP, CALL. 
    #    Code block memory positions is still unknown.
    # 2. Get memory length of each code block.
    # 3. Place functions in memory space.
    # 4. Fill in function references.

    for block in code_blocks:
        block_instructions, comments = compile_block(block, code_blocks)
        for idx, inst in enumerate(block_instructions):
            out = inst.__repr__()
            if idx in comments:
                out += "\t# " + comments[idx]
            print(out)
        # print(json.dumps(ass, indent=2))

    return code_blocks

if __name__ == "__main__":
    code_blocks = parse_file("test1.alang")
    try:
        compiled = compile_alang(code_blocks)
    except CompilationError as e:
        print(e)
    # print(json.dumps(compiled, indent=2))