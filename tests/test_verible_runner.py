from unittest.mock import Mock, patch

from runners.verible_runner import run_lint


def test_run_lint_returns_structured_result() -> None:
    fake_result = Mock()
    fake_result.stdout = "lint ok"
    fake_result.stderr = ""
    fake_result.returncode = 0

    with patch("runners.verible_runner.subprocess.run", return_value=fake_result) as fake_run:
        result = run_lint("rtl/counter.sv")

    fake_run.assert_called_once_with(
        "verible-verilog-lint rtl/counter.sv",
        shell=True,
        capture_output=True,
        text=True,
    )

    assert result == {
        "tool": "verible-verilog-lint",
        "target": "rtl/counter.sv",
        "command": "verible-verilog-lint rtl/counter.sv",
        "stdout": "lint ok",
        "stderr": "",
        "returncode": 0,
        "passed": True,
    }