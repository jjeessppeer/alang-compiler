from alang_parser import parse_file, Statement, IfStatement
import json
import re

# https://regex-vis.com/
variable_rgx = r"([*&])?(\w+)"
func_call_rgx = r"(\w+)\((([*&]?\w+,)*[*&]?\w+)?\)"
return_rgx = r"return( (([*&])?(\w+)))?"
if_rgx = r"(if|while)\(([\w*&]+)(!=|<|>)([\w*&]+)\)"

class CompilationError(Exception): pass

class Instruction():
    def __init__(self, op, grx=0, m=0, data=0):
        self.op = op
        self.grx = grx
        self.m = m
        self.data = data

    def __repr__(self):
        return f"{self.op} {self.grx} {self.m} {self.data}"
    
class CallPlaceholder():
    """Placeholder for call instruction before functions have been placed in memory. Used by function calls."""
    def __init__(self, block_id):
        self.block_id = block_id
    def __repr__(self):
        return f"CALL_PLACEHOLDER {self.block_id}"
    
class JmpToPlaceholder():
    """Placeholder for jmp instruction before functions have been placed in memory. Used by if and while."""
    def __init__(self, op, block_id, idx):
        self.op = op
        self.block_id = block_id
        self.idx = idx
    def __repr__(self):
        return f"{self.op}_PLACEHOLDER to:{self.block_id} idx:{self.idx}"
    
class JmpBackPlaceholder():
    """Placeholder for jmp instruction before functions have been placed in memory. Used by if and while."""
    def __repr__(self):
        return f"JMP_BACK_PLACEHOLDER"

def get_block(block_id, blocks):
    for b in blocks:
        if b["block_id"] == block_id:
            return b
    raise CompilationError("Trying to access non existant code block.")

def deref_variable(adr_op, var_name, var_map):
    """Dereference a variable. Return the address and mode of the given variable."""
    try:
        # The value is a constant
        val = int(var_name, 0)
        m = 1
        if adr_op == "*":
            m = 0
        elif adr_op == "&":
            raise CompilationError(f"Invalid address mode for constant.")
    except:
        # The value is a variable
        m = 0
        if adr_op == "&":
            m = 1
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
        
    instructions.append(CallPlaceholder(func_code))
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
    
def parse_variable(expression, require_valid=False):
    if r := re.match(variable_rgx, expression):
        adr_op = r.group(1)
        var_name = r.group(2)
        _, width = r.span()
        return adr_op, var_name, width
    if require_valid:
        raise CompilationError("Invalid variable syntax.")
    return False

def compile_expression(expression, block, all_blocks):
    """Compile an expression (x+y+z)"""
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
    """Compile value assignment (x=)."""
    v = parse_variable(assign_target)
    if not v:
        raise CompilationError(f"Unknown variable {assign_target}")
    adr_op, var_name, _ = v
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