import subprocess

def run_lint():
    """
    Runs the Verible Verilog linting tool on the specified RTL files.
    """
    cmd = "verible-verilog-lint rtl/*.v"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode
    }