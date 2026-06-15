from unittest.mock import Mock, patch
from runners.vhdl_runner import run_vhdl_lint

def test_run_vhdl_lint_returns_structured_result()-> None:
    fake_result = Mock()
    fake_result.stdout = "vhdl ok"
    fake_result.stderr = ""
    fake_result.returncode = 0

    with patch("runners.vhdl_runner.subprocess.run", return_value=fake_result) as fake_run:
        result = run_vhdl_lint("rtl/core.vhdl")
    
    fake_run.assert_called_once_with(
        "ghdl -a rtl/core.vhdl",
        shell = True,
        capture_output = True,
        text = True,
    )

    assert result == {
        "tool": "ghdl",
        "target": "rtl/core.vhdl",
        "command": "ghdl -a rtl/core.vhdl",
        "stdout": "vhdl ok",
        "stderr": "",
        "returncode": 0,
        "passed": True,
    }
