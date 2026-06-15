from ingestion.codebase_ingestion import is_supported_repo_file


def test_is_supported_repo_file_accepts_hdl_and_docs() -> None:
    assert is_supported_repo_file("rtl/counter.sv") is True
    assert is_supported_repo_file("rtl/core.vhdl") is True
    assert is_supported_repo_file("docs/reset.md") is True
    assert is_supported_repo_file("notes/design.txt") is True


def test_is_supported_repo_file_rejects_unsupported_files() -> None:
    assert is_supported_repo_file("images/waveform.png") is False
    assert is_supported_repo_file("build/output.json") is False
    assert is_supported_repo_file(".gitignore") is False