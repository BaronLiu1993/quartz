from unittest.mock import patch
from agents.execution_agent import execute_target, execute_targets, all_results_passed, is_verilog_target, is_vhdl_target, get_hdl_targets, execute_changed_files

def test_execute_target_runs_vhdl_lint_for_vhdl_file()-> None:
    expected_result = {
        "tool": "ghdl",
        "target": "rtl/core.vhdl",
        "command": "ghdl -a rtl/core.vhdl",
        "stdout": "vhdl ok",
        "stderr": "",
        "returncode": 0,
        "passed": True,
    }

    with patch("agents.execution_agent.run_vhdl_lint", return_value=expected_result) as fake_run_vhdl_lint:
        result = execute_target("rtl/core.vhdl")
    
    assert result == expected_result
    fake_run_vhdl_lint.assert_called_once_with("rtl/core.vhdl")

def test_execute_target_runs_verible_lint_for_verilog_file() -> None:
    expected_result = {
        "tool": "verible-verilog-lint",
        "target": "rtl/counter.sv",
        "command": "verible-verilog-lint rtl/counter.sv",
        "stdout": "lint ok",
        "stderr": "",
        "returncode": 0,
        "passed": True,
    }

    with patch("agents.execution_agent.run_lint", return_value=expected_result) as fake_run_lint:
        result = execute_target("rtl/counter.sv")

    assert result == expected_result
    fake_run_lint.assert_called_once_with("rtl/counter.sv")
        
def test_execute_target_runs_verible_lint_for_uppercase_verilog_file() -> None:
    expected_result = {
        "tool": "verible-verilog-lint",
        "target": "rtl/counter.SV",
        "command": "verible-verilog-lint rtl/counter.SV",
        "stdout": "lint ok",
        "stderr": "",
        "returncode": 0,
        "passed": True,
    }

    with patch("agents.execution_agent.run_lint", return_value=expected_result) as fake_run_lint:
        result = execute_target("rtl/counter.SV")

    assert result == expected_result
    fake_run_lint.assert_called_once_with("rtl/counter.SV")

def test_execute_targets_runs_each_target_and_combines_results() -> None:
    counter_result = {"target": "rtl/counter.sv", "passed": True}
    core_result = {"target": "rtl/core.vhdl", "passed": True}

    with patch(
        "agents.execution_agent.execute_target",
        side_effect=[counter_result, core_result],
    ) as fake_execute_target:
        result = execute_targets(["rtl/counter.sv", "rtl/core.vhdl"])

    assert fake_execute_target.call_args_list[0].args == ("rtl/counter.sv",)
    assert fake_execute_target.call_args_list[1].args == ("rtl/core.vhdl",)

    assert result == {
        "targets": ["rtl/counter.sv", "rtl/core.vhdl"],
        "results": [counter_result, core_result],
        "passed": True,
    }


def test_execute_targets_returns_message_when_no_targets() -> None:
    result = execute_targets([])

    assert result == {
        "targets": [],
        "results": [],
        "passed": None,
        "message": "No HDL targets provided.",
    }

def test_all_results_passed_returns_true_when_all_pass() -> None:
    results = [
        {"target": "rtl/counter.sv", "passed": True},
        {"target": "rtl/core.vhdl", "passed": True},
    ]

    assert all_results_passed(results) is True


def test_all_results_passed_returns_false_when_any_fail() -> None:
    results = [
        {"target": "rtl/counter.sv", "passed": True},
        {"target": "rtl/core.vhdl", "passed": False},
    ]

    assert all_results_passed(results) is False

def test_execute_target_returns_unsupported_for_non_hdl_file() -> None:
    result = execute_target("docs/readme.md")

    assert result == {
        "tool": None,
        "target": "docs/readme.md",
        "command": None,
        "stdout": "",
        "stderr": "Unsupported HDL target type.",
        "returncode": None,
        "passed": False,
    }

def test_is_vhdl_target_detects_vhdl_extensions() -> None:
    assert is_vhdl_target("rtl/core.vhd") is True
    assert is_vhdl_target("rtl/core.VHDL") is True
    assert is_vhdl_target("rtl/core.sv") is False


def test_is_verilog_target_detects_verilog_extensions() -> None:
    assert is_verilog_target("rtl/counter.v") is True
    assert is_verilog_target("rtl/counter.SV") is True
    assert is_verilog_target("rtl/counter.vhdl") is False

def test_get_hdl_targets_keeps_only_supported_hdl_files() -> None:
    files = [
        "rtl/counter.sv",
        "rtl/adder.V",
        "rtl/core.vhdl",
        "rtl/pkg.VHD",
        "docs/readme.md",
        "scripts/build.py",
    ]

    result = get_hdl_targets(files)

    assert result == [
        "rtl/counter.sv",
        "rtl/adder.V",
        "rtl/core.vhdl",
        "rtl/pkg.VHD",
    ]

def test_execute_changed_files_filters_to_hdl_targets_before_execution() -> None:
    files = [
        "rtl/counter.sv",
        "docs/readme.md",
        "rtl/core.vhdl",
    ]

    expected_result = {
        "targets": ["rtl/counter.sv", "rtl/core.vhdl"],
        "results": [],
        "passed": True,
    }

    with patch("agents.execution_agent.execute_targets", return_value=expected_result) as fake_execute_targets:
        result = execute_changed_files(files)

    fake_execute_targets.assert_called_once_with(["rtl/counter.sv", "rtl/core.vhdl"])
    assert result == expected_result


def test_execute_changed_files_returns_no_targets_message_when_no_hdl_files() -> None:
    result = execute_changed_files(["README.md", "docs/readme.md"])

    assert result == {
        "targets": [],
        "results": [],
        "passed": None,
        "message": "No HDL targets provided.",
    }
