from runners.vhdl_runner import run_vhdl_lint
from runners.verible_runner import run_lint


def is_verilog_target(target: str):
    normalized_target = target.lower()
    return normalized_target.endswith(".v") or normalized_target.endswith(".sv")


def is_vhdl_target(target: str):
    normalized_target = target.lower()
    return normalized_target.endswith(".vhd") or normalized_target.endswith(".vhdl")


def execute_target(target: str):
    if is_vhdl_target(target):
        return run_vhdl_lint(target)

    if is_verilog_target(target):
        return run_lint(target)

    return {
        "tool": None,
        "target": target,
        "command": None,
        "stdout": "",
        "stderr": "Unsupported HDL target type.",
        "returncode": None,
        "passed": False,
    }


def all_results_passed(results: list[dict]) -> bool:
    for result in results:
        if result.get("passed") is not True:
            return False
    return True


def execute_targets(targets: list[str]):
    if not targets:
        return {
            "targets": [],
            "results": [],
            "passed": None,
            "message": "No HDL targets provided.",
        }

    results = []
    for target in targets:
        results.append(execute_target(target))

    return {
        "targets": targets,
        "results": results,
        "passed": all_results_passed(results),
    }


def get_hdl_targets(files: list[str]) -> list[str]:
    hdl_targets = []

    for file in files:
        if is_verilog_target(file) or is_vhdl_target(file):
            hdl_targets.append(file)

    return hdl_targets


def execute_changed_files(files: list[str]):
    hdl_targets = get_hdl_targets(files)
    return execute_targets(hdl_targets)
