import subprocess

def run_vhdl_lint(target:str):
    """ Runs GHDL analysis on a VHDL file."""
    cmd = f"ghdl -a {target}"
    result = subprocess.run(cmd,shell= True, capture_output= True, text= True)

    return{
        "tool":"ghdl",
        "target": target,
        "command": cmd,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
        "passed": result.returncode == 0,
    }