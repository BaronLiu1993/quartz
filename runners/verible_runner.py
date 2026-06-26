import subprocess

DEFAULT_LINT_TARGET = "rtl/*.v rtl/*.sv"
def run_lint(target:str = DEFAULT_LINT_TARGET):
    """
    Runs the Verible Verilog linting tool on the specified RTL files.
    """
    args = ["verible-verilog-lint", target]
    cmd = " ".join(args)
    result = subprocess.run(args, capture_output=True, text=True)
    return {
        "tool": "verible-verilog-lint",
        "target":target,
        "command": cmd,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
        "passed": result.returncode == 0,
    }
