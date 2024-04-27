from alang_parser import parse_file
import json
import re

class CompilationError(Exception): pass

class Instruction():
    def __init__(self, op, grx=0, m=0, data=0):
        self.op = op
        self.grx = grx
        self.m = m
        self.data = data

    def __repr__(self):
        return f"{self.op} {self.grx} {self.m} {self.data}"

def get_block(block_id, blocks):
    for b in blocks:
        if b["block_id"] == block_id:
            return b
    raise CompilationError("Trying to access non existant code block.")

def deref_variable(adr_op, var_name, var_map):
    m = 0
    try:
        # The value is a constant
        val = int(var_name, 0)
        m = 1
    except:
        if adr_op == "&":
            m = 1
            var_name = var_name[1:]
        elif adr_op == "*":
            m = 2
        if var_name not in var_map:
            raise CompilationError(f"Undeclared variable used: {var_name}")
        val = var_map[var_name]
    return m, val

OP_MAP = {
    "+": "ADD",
    "-": "SUB",
    "*": "MUL",
    "=": "STORE"
}

variable_rgx = r"([*&])?(\w+)"
func_call_rgx = r"(\w+)\((([*&]?\w+,)*[*&]?\w+)?\)"

def compile_func_call(fn_name, fn_params, block, all_blocks):
    func_map = block["functions"]
    if fn_name not in func_map:
        raise CompilationError(f"Undeclared function used: {fn_name}")
    func_code = func_map[fn_name]

    instructions = []
    instructions.append(Instruction("PUSH", 0)) # Stash GR0

    # Set function parameter variables
    target_block = get_block(func_code, all_blocks)
    for idx, param in enumerate(fn_params):
        v = parse_variable(param)
        if not v:
            raise CompilationError(f"Invalid value syntax {param}")
        
        # Load the local variable
        adr_op, var_name, _ = v
        m, val = deref_variable(adr_op, var_name, block["variables"])
        instructions.append(Instruction("LOAD", 0, m, val)) 

        # Store in the target variable
        _, val = deref_variable(None, target_block["parameters"][idx], target_block["variables"])
        instructions.append(Instruction("STORE", 0, 0, val)) # Store in function variable
        
    instructions.append(Instruction("CALL", 0, 1, func_code))
    instructions.append(Instruction("POP", 0)) # Retrieve stashed GR1
    return instructions

def parse_function(expression):
    if r := re.match(func_call_rgx, expression):
        fn_name = r.group(1)
        fn_params = []
        if r.group(2):
            fn_params = r.group(2).split(",")
        _, width = r.span()
        return fn_name, fn_params, width
    else:
        return False
    
def parse_variable(expression):
    if r := re.match(variable_rgx, expression):
        adr_op = r.group(1)
        var_name = r.group(2)
        _, width = r.span()
        return adr_op, var_name, width
    return False

def compile_expression(expression, block, all_blocks):
    instructions = []
    print("COMPILING EXPRESSION", expression)
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
    print(instructions)
    return instructions


def compile_block(block, all_blocks):
    """Compile a code block to assembly instructions."""
    assembly_instructions = []
    for statement in block["code"]:
        s = statement[0].replace(" ", "") # Trim spaces.
        lhs, eq, rhs = s.partition("=")
        if not eq:
            rhs = lhs
            lhs = None
        expression_instructions = compile_expression(rhs, block, all_blocks)
        assembly_instructions += expression_instructions
        
        # print(s)
        # instruction = operation_to_assembly(operation, block)
        # assembly_instructions += instr
    return assembly_instructions
    
def compile_alang(code_blocks):
    # Compilation process.
    # 1. Compile all code blocks to assembly. 
    #    Insert temporary instructions in place of JMP, CALL. 
    #    Code block memory positions is still unknown.
    # 2. Get memory length of each code block.
    # 3. Place functions in memory space.
    # 4. Fill in function references.

    for block in code_blocks:
        ass = compile_block(block, code_blocks)

        # print(json.dumps(ass, indent=2))

    return code_blocks

if __name__ == "__main__":
    code_blocks = parse_file("test1.alang")
    try:
        compiled = compile_alang(code_blocks)
    except CompilationError as e:
        print(e)
    # print(json.dumps(compiled, indent=2))