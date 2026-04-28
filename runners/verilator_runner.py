import subprocess
from pydantic import BaseModel

class TestInputModel(BaseModel):
    user_id: str
    session_id: str
    code: str

def run_test(input: TestInputModel):
    """
    Runs the Verilator simulation on the specified testbench and RTL files.
    """
    cmd = f"verilator -Wall --cc rtl/{input.session_id}_{input.user_id}.v --exe tests/tb_adder.cpp"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode
    }