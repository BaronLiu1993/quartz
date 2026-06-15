from unittest.mock import Mock, patch

from runners.quartus_runner import run_quartus_compile


def test_run_quartus_compile_returns_structured_result() -> None:
    fake_result = Mock()
    fake_result.stdout = "compile ok"
    fake_result.stderr = ""
    fake_result.returncode = 0

    with patch("runners.quartus_runner.subprocess.run", return_value=fake_result) as fake_run:
        result = run_quartus_compile("fpga/top")

    fake_run.assert_called_once_with(
        "quartus_sh --flow compile fpga/top",
        shell=True,
        capture_output=True,
        text=True,
    )

    assert result == {
        "tool": "quartus_sh",
        "target": "fpga/top",
        "command": "quartus_sh --flow compile fpga/top",
        "stdout": "compile ok",
        "stderr": "",
        "returncode": 0,
        "passed": True,
    }
