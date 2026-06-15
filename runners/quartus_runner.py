import subprocess


def run_quartus_compile(target: str):
    """Run a Quartus compile flow for a project target."""
    cmd = f"quartus_sh --flow compile {target}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    return {
        "tool": "quartus_sh",
        "target": target,
        "command": cmd,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
        "passed": result.returncode == 0,
    }
