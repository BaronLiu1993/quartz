from ingestion.codebase_ingestion import fetch_github_file_text, is_supported_repo_file,is_md_file, is_txt_file, is_supported_repo_files, fetch_github_repo_tree, fetch_supported_repo_paths
from unittest.mock import Mock, MagicMock, patch

def test_is_supported_repo_file_accepts_hdl_and_docs() -> None:
    assert is_supported_repo_file("rtl/counter.sv") is True
    assert is_supported_repo_file("rtl/core.vhdl") is True
    assert is_supported_repo_file("docs/reset.md") is True
    assert is_supported_repo_file("notes/design.txt") is True

def test_is_supported_repo_file_rejects_unsupported_files() -> None:
    assert is_supported_repo_file("images/waveform.png") is False
    assert is_supported_repo_file("build/output.json") is False
    assert is_supported_repo_file(".gitignore") is False

def test_is_md_file_detects_markdown_case_insensitively() -> None:
    assert is_md_file("docs/reset.md") is True
    assert is_md_file("docs/reset.MD") is True
    assert is_md_file("docs/reset.txt") is False

def test_is_txt_file_detects_text_case_insensitively() -> None:
    assert is_txt_file("notes/design.txt") is True
    assert is_txt_file("notes/design.TXT") is True
    assert is_txt_file("notes/design.md") is False

def test_get_supported_repo_files_keeps_only_supported_files() -> None:
    paths = [
        "rtl/counter.sv",
        "rtl/core.vhdl",
        "docs/reset.MD",
        "notes/design.TXT",
        "images/waveform.png",
        "build/output.json",
    ]

    result = is_supported_repo_files(paths)

    assert result == [
        "rtl/counter.sv",
        "rtl/core.vhdl",
        "docs/reset.MD",
        "notes/design.TXT",
    ]

def test_fetch_github_file_text_fetches_decoded_content() -> None:
    fake_response = Mock()
    fake_response.json.return_value = {
        "content": "bW9kdWxlIGNvdW50ZXI7IGVuZG1vZHVsZQ==",
        "encoding": "base64",
    }

    fake_client = Mock()
    fake_client.get.return_value = fake_response

    fake_context = MagicMock()
    fake_context.__enter__.return_value = fake_client
    fake_context.__exit__.return_value = None

    with patch("ingestion.codebase_ingestion.httpx.Client", return_value=fake_context):
        result = fetch_github_file_text("octo/demo", "rtl/counter.sv", "main")

    assert result == "module counter; endmodule"
    fake_client.get.assert_called_once_with(
        "https://api.github.com/repos/octo/demo/contents/rtl/counter.sv",
        params={"ref": "main"},
    )
    fake_response.raise_for_status.assert_called_once()

def test_fetch_github_repo_tree_returns_blob_paths() -> None:
    fake_response = Mock()
    fake_response.json.return_value = {
        "tree": [
            {"path": "rtl/counter.sv", "type": "blob"},
            {"path": "rtl", "type": "tree"},
            {"path": "docs/reset.md", "type": "blob"},
        ]
    }

    fake_client = Mock()
    fake_client.get.return_value = fake_response

    fake_context = MagicMock()
    fake_context.__enter__.return_value = fake_client
    fake_context.__exit__.return_value = None

    with patch("ingestion.codebase_ingestion.httpx.Client", return_value=fake_context):
        result = fetch_github_repo_tree("octo/demo", "main")

    assert result == ["rtl/counter.sv", "docs/reset.md"]
    fake_client.get.assert_called_once_with(
        "https://api.github.com/repos/octo/demo/git/trees/main",
        params={"recursive": "1"},
    )
    fake_response.raise_for_status.assert_called_once()

def test_fetch_supported_repo_paths_filters_repo_tree() -> None:
    with patch(
        "ingestion.codebase_ingestion.fetch_github_repo_tree",
        return_value=[
            "rtl/counter.sv",
            "docs/reset.md",
            "images/waveform.png",
        ],
    ) as fake_fetch_tree:
        result = fetch_supported_repo_paths("octo/demo", "main")

    fake_fetch_tree.assert_called_once_with("octo/demo", "main")
    assert result == ["rtl/counter.sv", "docs/reset.md"]

def test_fetch_supported_repo_paths_returns_empty_when_no_supported_files() -> None:
    with patch(
        "ingestion.codebase_ingestion.fetch_github_repo_tree",
        return_value=[
            "images/waveform.png",
            "build/output.json",
        ],
    ):
        result = fetch_supported_repo_paths("octo/demo", "main")

    assert result == []