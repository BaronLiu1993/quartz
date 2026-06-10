import subprocess

DEFAULT_LINT_TARGET = "rt1/*.v rt1/*.sv"
def run_lint(target:str = DEFAULT_LINT_TARGET):
    """
    Runs the Verible Verilog linting tool on the specified RTL files.
    """
    cmd = f"verible-verilog-lint {target}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return {
        "tool": "verible-verilog-lint",
        "target":target,
        "command": cmd,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
        "passed": result.returncode == 0,
    }