
import re
import json

# Matches the start of any text
text_start_rgx = r"[^ \n\r\t]"

# Line comment
# https://regex-vis.com/?r=%23%5B%5E%5Cn%5D*
line_comment_rgx = r"#[^\n]*"

# Function definition
# https://regex-vis.com/?r=function+%28%5Cw%2B%29%5C%28%28%28%5Cw%2B%2C%29*%5Cw%2B%29%3F%5C%29%5B+%5Cn%5Cr%5D*%5C%7B
fn_def_rgx = r"function (\w+)\(((\w+,)*\w+)?\)[ \n\r]*\{"

# Function call
# https://regex-vis.com/?r=%28%5Cw%2B%29%5C%28%28%28%5B*%26%5D%3F%5Cw%2B%2C%29*%5B*%26%5D%3F%5Cw%2B%29%3F%5C%29%3B
fn_call_rgx = r"(\w+)\((([*&]?\w+,)*[*&]?\w+)?\);"

# Variable assignment
# https://regex-vis.com/?r=%5Cw%2B+*%3D+*%5B%5Cw%5C%2B%5C-%5C*%5C%26%5D%2B+*%28%3F%3D%3B%29
# https://regex-vis.com/?r=+*%28%5B*%26%5D%3F%5Cw%2B%29+*%3D+*%28%5B*%26%5D%3F%5Cw%2B%29+*%28%5B%5C%2B%5C*%5C-%5D+*%28%5B*%26%5D%3F%5Cw%2B%29%29*%3B
assignment_rgx = r" *([*&]?\w+) *= *([*&]?\w+) *([\+\*\-] *([*&]?\w+))*;"
copy_assignment_rgx = r"(\w+)$"
math_assignment_rgx = r"([*&]?\w+)([\+\-\*])([*&]?\w+)$"
func_assignment_rgx = r"(\w+)\((([*&]?\w+,)*[*&]?\w+)?\)$"

# Variable declaration
variable_declaration_rgx = r"var (\w+);"

# Match any statement.
# https://regex-vis.com/?r=%28%5B%5Cw+%5C%28%5C%29%2C%5C%2B%5C-%5C*%3D%5D%2B%29%3B
statement_rgx = r"([\w \(\),\+\-\*=&]+);"

class ParseError(Exception): pass
class CompilationError(Exception): pass

def get_row_number(text, index):
    """Return the row number of the specified text index."""
    n = 1
    for character in text[0:index]:
        if character == "\n": 
            n += 1
    return n

def parse_assignment(statement, variables, functions):
    """Parse a variable assignment statement."""
    statement = statement.replace(" ", "") # Clean up spaces
    [lhs, _, rhs] = statement.partition("=")

    if r := re.match(copy_assignment_rgx, rhs):
        # Assignment from single value.
        operation = {
            "type": "assign_copy",
            "target": lhs,
            "source": r.group(1)
        }
    elif r := re.match(math_assignment_rgx, rhs):
        # Assignment to variable from expression.
        operation = {
            "type": "assign_math",
            "target": lhs,
            "source": [r.group(1), r.group(3)],
            "operand": r.group(2)
        }
    elif r := re.match(func_assignment_rgx, rhs):
        # Assignment to variable from function call.
        params = []
        if r.group(2):
            params = r.group(2).split(",")
        operation = {
            "type": "assign_func",
            "target": lhs,
            "func_name": r.group(1),
            "func_params": params
        }
    else:
        raise ParseError(f"Invalid assignment syntax. \"statement\"")

    return [operation]

def parse_function_call(fn_name, operands, variables, functions):
    # TODO: Validate that variables and function exists.
    return {
        "type": "function_call",
        "target_fn": fn_name,
        "operands": operands
    }



def parse_code_block(text, start_index, block_type, block_count, variable_count, variables, functions):
    """Parse a function block of code. Exit on }."""
    statements = []
    code_blocks = {}
    block_id = block_count
    i = start_index
    while i < len(text):
        # Seek forwards until next word
        if re.match(text_start_rgx, text[i]):
            t = text[i:]
            if r := re.match(line_comment_rgx, t):
                # Skip past line comments.
                _, comment_end = r.span()
                i = i + comment_end

            elif text[i] == "}":
                # End of code block.
                break

            elif r := re.match(fn_def_rgx, t):
                # Parse function definition and content.
                name = r.group(1)
                params = []
                if (r.group(2)):
                    params = r.group(2).split(",")
                
                # Add parameters to avaiable variables.
                # v = variables.copy()
                v = {}
                for p in params:
                    v[p] = variable_count
                    variable_count += 1
                
                # Parse the code block containing the function code.
                _, block_start = r.span()
                fn_block, i, block_count, variable_count = parse_code_block(
                    text, 
                    i + block_start + 1,
                    "function",
                    block_count+1,
                    variable_count,
                    v,
                    {})

                fn_block["name"] = name
                fn_block["parameters"] = params
                functions[name] = fn_block["block_id"]
                code_blocks[fn_block["block_id"]] = fn_block

            elif r := re.match(variable_declaration_rgx, t):
                # Parse variable declaration.
                _, width = r.span()
                i += width
                name = r.group(1)
                variables[name] = variable_count
                variable_count += 1
            
            elif r := re.match(statement_rgx, t):
                statements.append([
                    r.group(1),
                    get_row_number(text, i)
                ])
                _, width = r.span()
                i += width
                
            else:
                print(text[i:i+20])
                l = 1
                for c in text[0:i]:
                    if c == "\n": l += 1
                raise ParseError(f"Parse failed. Invalid syntax starting at line {l}")
        i += 1

    return (
        {
            "block_type": block_type,
            "block_id": block_id,
            "span": [start_index, i],
            "variables": variables,
            "functions": functions,
            "code": statements,
            "code_blocks": code_blocks
        }, 
        i, block_count, variable_count)

def flatten_code_tree(parent_block):
    """Flatten the nestled code blocks into a list."""
    # blocks = {}
    blocks = []
    for id, child_block in parent_block["code_blocks"].items():
        # Child blocks should access the variables and functions of the parent block.
        # Do not overwrite local variables.
        for v_name, v_id in parent_block["variables"].items():
            if v_name not in child_block["variables"]:
                child_block["variables"][v_name] = v_id
        for f_name, f_id in parent_block["functions"].items():
            if f_name not in child_block["functions"]:
                child_block["functions"][f_name] = f_id

        # child_block["parent_id"] = parent_block["block_id"]
        # Recurse through child blocks.
        # blocks[id] = flatten_code_tree(child_block)
        blocks += flatten_code_tree(child_block)
    del parent_block["code_blocks"] # Delete tree structure.
    return [parent_block] + blocks
    # return parent_block | blocks

def parse_file(path):
    f = open(path, "r")
    lines = f.readlines()
    text = "".join(lines)
    try:
        code_tree, _, _, _ = parse_code_block(text, 0, "global", -1, 0, {}, {})
        # print(json.dumps(code_tree, indent=2))

        if len(code_tree["code"]) != 0:
            raise ParseError("Parse failed. No code apart from variable and function declarations allowed in the global scope. Put it in the a function.")
        if "main" not in code_tree["functions"]:
            raise ParseError("Parse failed. No main function defined.")
    except ParseError as e:
        print(e)
        exit()

    code_blocks = flatten_code_tree(code_tree)
    print(json.dumps(code_blocks, indent=2))
    return code_blocks

if __name__ == "__main__":
    parse_file("test1.alang")
    # print(json.dumps(parse_file("test1.alang"), indent=2))