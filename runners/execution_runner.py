import subprocess
import uuid
from pydantic import BaseModel
from time import sleep

class RequestModel(BaseModel):
    user_id: str
    session_id: str

# Create docker container to run code
def run_job(request: RequestModel):
    image_name = f"quartz-sandbox-{request.session_id}-{request.user_id}"
    subprocess.run(
        ["docker", "build", "-f", "sandbox/sandbox.Dockerfile", "-t", image_name, "sandbox"],
        check=True
    )
    result = subprocess.run(
        [
            "docker", "run",
            "--rm",
            "--network=none",
            "--memory=512m",
            "--cpus=1",
            image_name
        ],
        capture_output=True,
        text=True
    )

    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode
    }

# Destroy docker container after execution
def destroy_job(request: RequestModel):
    image_name = f"quartz-sandbox-{request.session_id}-{request.user_id}"
    subprocess.run(["docker", "rmi", "-f", image_name], check=True)

def run_execution(request: RequestModel):
    """
    Runs the execution of the compiled Verilog code on the specified testbench.
    Perform this operation in a sandboxed environment.
    """
    # Create a docker container to isolate execution
    cmd = "./obj_dir/Vtb_adder"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode
    }