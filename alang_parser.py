
import re
import json

class ParseError(Exception): pass
class CompilationError(Exception): pass

class Statement():
    def __init__(self, text, row):
        self.text = text
        self.row = row

class IfStatement(Statement):
    def __init__(self, text, row, target_block):
        super().__init__(text, row)
        # self.text = text
        self.target_block = target_block
    def __repr__(self):
        return f"{self.text} => {self.target_block}"


# https://regex-vis.com/
text_start_rgx = r"[^ \n\r\t]"
line_comment_rgx = r"//[^\n]*"
fn_def_rgx = r"function (\w+)\(((\w+,)*\w+)?\)[ \n\r]*\{"
if_def_rgx = r"((if|while) *\(([*&]?\w+)([<>]|!=)([*&]?\w+)\))[ \n\r]*\{"
variable_declaration_rgx = r"int (\w+);"
statement_rgx = r"([\w \(\),\+\-\*=&]+);"

def get_row_number(text, index):
    """Return the row number of the specified text index."""
    n = 1
    for character in text[0:index]:
        if character == "\n": 
            n += 1
    return n

def parse_code_block(text, start_index, block_type, block_count, variable_count, parent_id, parameters = []):
    """Parse a function block of code. Exit on }."""
    statements = []
    code_blocks = {}
    functions = {}
    variables = {}
    block_id = block_count

    # Add parameters to local variables
    for p in parameters:
        variables[p] = variable_count
        variable_count += 1
    
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
                
                # Parse the code block containing the function code.
                _, block_start = r.span()
                fn_block, i, block_count, variable_count = parse_code_block(
                    text, 
                    i + block_start + 1,
                    "function",
                    block_count+1,
                    variable_count,
                    block_id,
                    params)

                fn_block["name"] = name
                fn_block["parameters"] = params
                functions[name] = fn_block["block_id"]
                code_blocks[fn_block["block_id"]] = fn_block

            elif r := re.match(if_def_rgx, t):
                # Parse the conditional code block
                row = get_row_number(text, i)
                _, block_start = r.span()
                if_block, i, block_count, variable_count = parse_code_block(
                    text, 
                    i + block_start + 1,
                    r.group(2),
                    block_count+1,
                    variable_count,
                    block_id
                    )
                code_blocks[if_block["block_id"]] = if_block

                s = r.group(1)
                statements.append(IfStatement(s, row, if_block["block_id"]))
                
            
            elif r := re.match(variable_declaration_rgx, t):
                # Parse variable declaration.
                _, width = r.span()
                i += width
                name = r.group(1)
                variables[name] = variable_count
                variable_count += 1
            
            elif r := re.match(statement_rgx, t):
                statements.append(Statement(r.group(1), get_row_number(text, i)))
                _, width = r.span()
                i += width
                
            else:
                l = 1
                for c in text[0:i]:
                    if c == "\n": l += 1
                raise ParseError(f"Parse failed. Invalid syntax starting at line {l}")
        i += 1

    return (
        {
            "block_type": block_type,
            "block_id": block_id,
            "name": "",
            "parent_block": parent_id,
            "variables": variables,
            "functions": functions,
            "code": statements,
            "code_blocks": code_blocks,
        }, 
        i, block_count, variable_count)

def flatten_code_tree(parent_block):
    """Flatten the nestled code blocks into a list."""
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

        # Recurse through child blocks.
        blocks += flatten_code_tree(child_block)
    del parent_block["code_blocks"] # Delete tree structure.
    return [parent_block] + blocks

def parse_file(path):
    f = open(path, "r")
    lines = f.readlines()
    text = "".join(lines)
    try:
        code_tree, _, _, _ = parse_code_block(text, 0, "global", -1, 0, None)
        # print(json.dumps(code_tree, indent=2))

        if len(code_tree["code"]) != 0:
            raise ParseError("Parse failed. No code apart from variable and function declarations allowed in the global scope. Put it in the a function.")
        if "main" not in code_tree["functions"]:
            raise ParseError("Parse failed. No main function defined.")
    except ParseError as e:
        print(e)
        exit()

    code_blocks = flatten_code_tree(code_tree)
    # print(json.dumps(code_blocks, indent=2, default=lambda x: x.__dict__))
    return code_blocks

if __name__ == "__main__":
    parse_file("test1.alang")
    # print(json.dumps(parse_file("test1.alang"), indent=2))