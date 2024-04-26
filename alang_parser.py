
import re
import json

# Matches the start of a statement
statement_start_rgx = r"[^ \n\r\t]"

# Matches a line comment
# https://regex-vis.com/?r=%23%5B%5E%5Cn%5D*
line_comment_rgx = r"#[^\n]*"

# Matches a function definition
# https://regex-vis.com/?r=function+%5Cw%2B%5C%28%28%28%5Cw%2B%2C%29*%5Cw%2B%29%3F%5C%29%5B+%5Cn%5Cr%5D*%5C%7B
fn_rgx = r"function \w+\(((\w+,)*\w+)?\)[ \n\r]*\{"

# Extract the name of a function
# https://regex-vis.com/?r=%28%3F%3C%3Dfunction+%29%5Cw%2B%28%3F%3D%5C%28%29
fn_name_rgx = r"(?<=function )\w+(?=\()"

# Match a variable assignment
# https://regex-vis.com/?r=%5Cw%2B+*%3D+*%5B%5Cw%5C%2B%5C-%5C*%5C%26%5D%2B+*%28%3F%3D%3B%29
assignment_rgx = r"\w+ *= *[\w\+\-\*\& ]+ *(?=;)"
copy_assignment_rgx = r"\w+$"
ref_assignment_rgx = r"\&\w+$"
ptr_assignment_rgx = r"\*\w+$"
add_assignment_rgx = r"(\w+)\+(\w+)$"

# Variable declaration
variable_declaration_rgx = r"var (\w+);"


def parse_function(fn_statement):
    name = re.search(fn_name_rgx, fn_statement).group()
    # variables
    return name

def parse_assignment(statement, variables, functions):
    """Parse a variable assignment statement."""
    statement = statement.replace(" ", "") # Clean up spaces
    [lhs, _, rhs] = statement.partition("=")
    
    target = lhs
    source = None
    assignment_type = None
    if r := re.match(copy_assignment_rgx, rhs):
        assignment_type = "copy"
        source = r.group()
    elif r := re.match(ref_assignment_rgx, rhs):
        assignment_type = "ref"
        source = r.group()[1:]
    elif r := re.match(ptr_assignment_rgx, rhs):
        assignment_type = "ptr"
        source = r.group()[1:]
    elif r := re.match(add_assignment_rgx, rhs):
        assignment_type = "add"
        source = [r.group(1), r.group(2)]

    # TODO: Validate that the variables are available.
    
    
    operation = {
        "type": "variable_assignment",
        "assignment_type": assignment_type,
        "target": target,
        "source": source
    }
    return operation

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
 

def parse_code_block(text, start_index, block_type, block_count, variable_count, variables, functions):
    """Parse a function block of code. Terminate on }."""
    print(variable_count)
    statements = []
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
            elif r := re.match(fn_rgx, t):
                # Parse function definition and content.
                name = parse_function(r.group())
                _, block_start = r.span()
                fn_block, i, block_count, variable_count = parse_code_block(
                    text, 
                    i + block_start + 1,
                    "function",
                    block_count+1,
                    variable_count,
                    variables.copy(),
                    functions.copy())
                
                functions[name] = fn_block["block_id"]
                statements.append(fn_block)

            elif r := re.match(assignment_rgx, t):
                # Parse variable assignment.
                _, width = r.span()
                s = parse_assignment(r.group(), variables, functions)
                statements.append(s)
                i += width

            elif r := re.match(variable_declaration_rgx, t):
                # Parse variable declaration.
                name = r.group(1)
                variables[name] = variable_count
                variable_count += 1
        i += 1
  

    return (
        {
        "block_type": block_type,
        "block_id": block_id,
        "variables": variables,
        "functions": functions,
        "content": statements
        }, 
        i, block_count, variable_count)


f = open("test1.cmm", "r")
lines = f.readlines()
text = "".join(lines)
w = parse_code_block(text, 0, "global", 0, 0, {}, {})
print(json.dumps(w[0], indent=2))
print(w[2], w[3])