from alang_parser import parse_file
import json

def get_code_blocks(code_block):
    blocks = []
    for id, block in code_block["code_blocks"].items():
        blocks += get_code_blocks(block)
    return [code_block] + blocks

    


def compile_alang(code_tree):
    # Un-nestle all code blocks
    # print(json.dumps(code_tree, indent=2))
    # print(json.dumps(code_tree["code_blocks"], indent=2))
    code_blocks = get_code_blocks(code_tree)
    for b in code_blocks:
        del b["code_blocks"]
    print(json.dumps(code_blocks, indent=2))

    return code_tree


if __name__ == "__main__":
    code_tree, _, _ = parse_file("test1.cmm")
    compiled = compile_alang(code_tree)
    # print(json.dumps(compiled, indent=2))