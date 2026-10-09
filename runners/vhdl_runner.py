import subprocess

def run_vhdl_lint(target:str):
    """ Runs GHDL analysis on a VHDL file."""
    args = ["ghdl", "-a", target]
    cmd = " ".join(args)
    result = subprocess.run(args, capture_output= True, text= True)

    return{
        "tool":"ghdl",
        "target": target,
        "command": cmd,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
        "passed": result.returncode == 0,
    }
