from alang_parser import parse_file
import json

def flatten_code_blocks(parent_block):
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

        child_block["parent_id"] = parent_block["block_id"]
        # Recurse through child blocks.
        blocks += flatten_code_blocks(child_block)
    return [parent_block] + blocks

def compile_alang(code_tree):
    # Un-nestle all code blocks
    code_blocks = flatten_code_blocks(code_tree)

    
    for b in code_blocks:
        del b["code_blocks"]
    print(json.dumps(code_blocks, indent=2))

    return code_tree

if __name__ == "__main__":
    code_tree, _, _ = parse_file("test1.cmm")
    compiled = compile_alang(code_tree)
    # print(json.dumps(compiled, indent=2))