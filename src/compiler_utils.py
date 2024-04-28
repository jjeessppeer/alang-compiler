import re

class CompilationError(Exception): pass

# https://regex-vis.com/
variable_rgx = r"([*&])?(\w+)(?=[+\-*;]|$)"
func_call_rgx = r"(\w+)\((([*&]?\w+,)*[*&]?\w+)?\)$"

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

def get_block(block_id, blocks):
    for b in blocks:
        if b["block_id"] == block_id:
            return b
    raise CompilationError("Trying to access non existant code block.")

def parse_function(expression):
    """Parse a function call statement and return relevant info."""
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
    """Parse a variable token and return relevant info."""
    if r := re.match(variable_rgx, expression):
        adr_op = r.group(1)
        var_name = r.group(2)
        _, width = r.span()
        return adr_op, var_name, width
    if require_valid:
        raise CompilationError("Invalid variable syntax.")
    return False

def instructions_to_string(instructions, comments={}):
    out = ""
    for idx, inst in enumerate(instructions):
        # out += f"{idx:02} "
        out += inst.__repr__()
        if idx in comments:
            out += "\t# " + comments[idx]
        out += "\n"
    return out

class Instruction():
    def __init__(self, op, grx=0, m=0, data=0):
        self.op = op
        self.grx = grx
        self.m = m
        self.data = data

    def __repr__(self):
        return f"{self.op} {self.grx} {self.m} {self.data}"
    
class JmpToPlaceholder():
    """Placeholder for jmp instruction before functions have been placed in memory. Used by if and while."""
    def __init__(self, op, block_id, offset):
        self.op = op
        self.block_id = block_id
        self.offset = offset
    def __repr__(self):
        return f"{self.op}_PLACEHOLDER to:{self.block_id} offset:{self.offset}"
    
class JmpBackPlaceholder():
    """Placeholder for jmp instruction before functions have been placed in memory. Used by if and while."""
    def __repr__(self):
        return f"JMP_BACK_PLACEHOLDER"