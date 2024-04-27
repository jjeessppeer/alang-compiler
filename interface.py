import os, json, sys
from alang_parser import parse_file
from alang_compiler import compile_alang
from assembler import assemble

if __name__ == "__main__":
    if len(sys.argv) < 2: 
        raise Exception("No input file specified.")
    input_file = sys.argv[1]

    os.makedirs("output", exist_ok=True)

    print("Parsing code...")
    code_blocks = parse_file(input_file)
    with open(f"output/parsed.json", "w") as f:
        f.write(json.dumps(code_blocks, indent=2, default=lambda x: x.__dict__))

    print("Compiling...")
    assembly_code = compile_alang(code_blocks)
    with open(f"output/compiled.asm", "w") as f:
        f.write(assembly_code)

    print("Assembling...")
    machine_code = assemble(assembly_code)
    with open(f"output/machine_code", "w") as f:
        f.write(machine_code)

