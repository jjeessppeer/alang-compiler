
import re
import json

# Matches the start of a statement
statement_start_rgx = r"[^ \n\r\t]"

# Matches a line comment
# https://regex-vis.com/?r=%23%5B%5E%5Cn%5D*
line_comment_rgx = r"#[^\n]*"

# Matches a function definition
# https://regex-vis.com/?r=function+%28%5Cw%2B%29%5C%28%28%28%5Cw%2B%2C%29*%5Cw%2B%29%3F%5C%29%5B+%5Cn%5Cr%5D*%5C%7B
fn_def_rgx = r"function (\w+)\(((\w+,)*\w+)?\)[ \n\r]*\{"

# Match a variable assignment
# https://regex-vis.com/?r=%5Cw%2B+*%3D+*%5B%5Cw%5C%2B%5C-%5C*%5C%26%5D%2B+*%28%3F%3D%3B%29
assignment_rgx = r"\w+ *= *[\w\+\-\*\& ]+ *(?=;)"
copy_assignment_rgx = r"\w+$"
ref_assignment_rgx = r"\&\w+$"
ptr_assignment_rgx = r"\*\w+$"
add_assignment_rgx = r"(\w+)\+(\w+)$"

# Variable declaration
variable_declaration_rgx = r"var (\w+);"

# Function call
fn_call_rgx = r"(\w+)\(((\w+,)*\w+)?\);"

def parse_assignment(statement, variables, functions):
    """Parse a variable assignment statement."""
    statement = statement.replace(" ", "") # Clean up spaces
    [lhs, _, rhs] = statement.partition("=")

    r = re.match(r"(([*&]?\w+)([\+\-\*]))?([*&]?\w+)$", rhs)
    
    if not r:
        raise Exception("Invalid syntax.")
    v1 = r.group(2)
    v2 = r.group(4)
    operand = r.group(3)
    if not operand:
        v1 = v2
    
    operations = []
    operations.append({
        "type": "load",
        "value": v1
    })
    
    if operand:
        # The second operand is not required.
        operations.append({
            "type": operand,
            "value": v2
        })

    operations.append({
        "type": "store",
        "value": lhs
    })

    return operations

    # a = b; =>
    # LOAD 0 0 [b_addr]
    # STORE 0 0 [a_addr]
    #
    # a = &b; =>
    # LOAD 0 1 [b_addr]
    # STORE 0 0 [a_addr]
    #
    # a = *b; =>
    # LOAD 0 3 [b_addr]
    # STORE 0 0 [a_addr]

def parse_function_call(fn_name, operands, variables, functions):
    # TODO: Validate that variables and function exists.
    return {
        "type": "function_call",
        "name": fn_name,
        "operands": operands
    }
 

def parse_code_block(text, start_index, block_type, block_count, variable_count, variables, functions):
    """Parse a function block of code. Terminate on }."""
    statements = []
    code_blocks = {}
    block_id = block_count
    i = start_index
    while i < len(text):
        # Seek forwards until next word
        if re.match(statement_start_rgx, text[i]):
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
                print("Spawning new function block", name)
                print(functions)
                fn_block, i, block_count, variable_count = parse_code_block(
                    text, 
                    i + block_start + 1,
                    "function",
                    block_count+1,
                    variable_count,
                    v,
                    {})

                fn_block["name"] = name
                functions[name] = fn_block["block_id"]
                code_blocks[fn_block["block_id"]] = fn_block

            elif r := re.match(assignment_rgx, t):
                # Parse variable assignment.
                _, width = r.span()
                i += width
                s = parse_assignment(r.group(), variables, functions)
                statements += s
                # statements.append(s)

            elif r := re.match(variable_declaration_rgx, t):
                # Parse variable declaration.
                _, width = r.span()
                i += width
                name = r.group(1)
                variables[name] = variable_count
                variable_count += 1

            elif r := re.match(fn_call_rgx, t):
                # Parse function call.
                _, width = r.span()
                i += width
                s = parse_function_call(r.group(1), r.group(2).split(","), variables, functions)
                statements.append(s)

            else:
                l = 1
                for c in text[0:i]:
                    if c == "\n": l += 1
                raise Exception(f"Parse failed. Invalid syntax line {l}")
        i += 1

    return (
        {
            "block_type": block_type,
            "block_id": block_id,
            "variables": variables,
            "functions": functions,
            "code": statements,
            "code_blocks": code_blocks
        }, 
        i, block_count, variable_count)

def parse_file(path):
    f = open(path, "r")
    lines = f.readlines()
    text = "".join(lines)
    w = parse_code_block(text, 0, "global", 0, 0, {}, {})
    # print(json.dumps(w[0], indent=2))
    return (w[0], w[2], w[3])

if __name__ == "__main__":
    print(json.dumps(parse_file("test1.cmm")[0], indent=2))
# print(w[2], w[3])
# print(json.dumps(w[4], indent=2))