from unittest.mock import Mock, MagicMock, patch

from ingestion.codebase_ingestion import (
    fetch_github_file_text,
    fetch_github_repo_tree,
    fetch_supported_repo_file_texts,
    fetch_supported_repo_paths,
    get_github_headers,
    get_supported_repo_files,
    infer_file_type,
    ingest_github_codebase,
    ingest_github_codebase_with_default_client,
    is_md_file,
    is_supported_repo_file,
    is_txt_file,
    process_repo_file_texts,
)

def test_get_github_headers_includes_token_when_available() -> None:
    with patch.dict("os.environ", {"GITHUB_TOKEN": "secret-token"}):
        headers = get_github_headers()

    assert headers["Authorization"] == "Bearer secret-token"
    assert headers["Accept"] == "application/vnd.github+json"

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

    result = get_supported_repo_files(paths)

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

def test_fetch_supported_repo_file_texts_fetches_text_for_supported_paths() -> None:
    with patch(
        "ingestion.codebase_ingestion.fetch_supported_repo_paths",
        return_value=[
            "rtl/counter.sv",
            "docs/reset.md",
        ],
    ) as fake_fetch_paths:
        with patch(
            "ingestion.codebase_ingestion.fetch_github_file_text",
            side_effect=[
                "module counter; endmodule",
                "# Reset behavior",
            ],
        ) as fake_fetch_text:
            result = fetch_supported_repo_file_texts("octo/demo", "main")

    fake_fetch_paths.assert_called_once_with("octo/demo", "main")
    assert fake_fetch_text.call_args_list[0].args == (
        "octo/demo",
        "rtl/counter.sv",
        "main",
    )
    assert fake_fetch_text.call_args_list[1].args == (
        "octo/demo",
        "docs/reset.md",
        "main",
    )

    assert result == [
        {
            "path": "rtl/counter.sv",
            "file_type": "sv",
            "text": "module counter; endmodule",
        },
        {
            "path": "docs/reset.md",
            "file_type": "md",
            "text": "# Reset behavior",
        },
    ]

def test_fetch_supported_repo_file_texts_returns_empty_when_no_supported_paths() -> None:
    with patch(
        "ingestion.codebase_ingestion.fetch_supported_repo_paths",
        return_value=[],
    ):
        with patch("ingestion.codebase_ingestion.fetch_github_file_text") as fake_fetch_text:
            result = fetch_supported_repo_file_texts("octo/demo", "main")

    fake_fetch_text.assert_not_called()
    assert result == []

def test_infer_file_type_returns_lowercase_extension() -> None:
    assert infer_file_type("rtl/counter.sv") == "sv"
    assert infer_file_type("rtl/core.VHDL") == "vhdl"
    assert infer_file_type("docs/reset.MD") == "md"

def test_process_repo_file_texts_processes_each_file_and_flattens_chunks() -> None:
    fake_client = object()

    counter_chunk = {"chunk_id": "counter_chunk"}
    reset_chunk = {"chunk_id": "reset_chunk"}

    file_texts = [
        {
            "path": "rtl/counter.sv",
            "file_type": "sv",
            "text": "module counter; endmodule",
        },
        {
            "path": "docs/reset.md",
            "file_type": "md",
            "text": "# Reset behavior",
        },
    ]

    with patch(
        "ingestion.codebase_ingestion.process_document",
        side_effect=[
            [counter_chunk],
            [reset_chunk],
        ],
    ) as fake_process_document:
        result = process_repo_file_texts(fake_client, file_texts)

    assert fake_process_document.call_args_list[0].kwargs == {
        "client": fake_client,
        "source": "rtl/counter.sv",
        "text": "module counter; endmodule",
        "file_type": "sv",
        "topic": "codebase",
    }

    assert fake_process_document.call_args_list[1].kwargs == {
        "client": fake_client,
        "source": "docs/reset.md",
        "text": "# Reset behavior",
        "file_type": "md",
        "topic": "codebase",
    }

    assert result == [counter_chunk, reset_chunk]

def test_ingest_github_codebase_fetches_and_processes_supported_files() -> None:
    fake_client = object()

    file_texts = [
        {"path": "rtl/counter.sv", "file_type": "sv", "text": "module counter; endmodule"},
        {"path": "docs/reset.md", "file_type": "md", "text": "# Reset"},
    ]

    chunks = [
        {"chunk_id": "counter_chunk"},
        {"chunk_id": "reset_chunk"},
    ]

    with patch(
        "ingestion.codebase_ingestion.fetch_supported_repo_file_texts",
        return_value=file_texts,
    ) as fake_fetch_file_texts:
        with patch(
            "ingestion.codebase_ingestion.process_repo_file_texts",
            return_value=chunks,
        ) as fake_process:
            result = ingest_github_codebase(
                fake_client,
                "octo/demo",
                "main",
                save_to_db=False,
            )

    fake_fetch_file_texts.assert_called_once_with("octo/demo", "main")
    fake_process.assert_called_once_with(fake_client, file_texts)

    assert result == {
        "repo_full_name": "octo/demo",
        "ref": "main",
        "files_ingested": 2,
        "chunks_created": 2,
        "saved_to_db": False,
        "chunks": chunks,
    }

def test_ingest_github_codebase_saves_chunks_when_enabled() -> None:
    fake_client = object()

    file_texts = [
        {
            "path": "rtl/counter.sv",
            "file_type": "sv",
            "text": "module counter; endmodule",
        }
    ]

    chunks = [
        {"chunk_id": "counter_chunk"},
    ]

    with patch(
        "ingestion.codebase_ingestion.fetch_supported_repo_file_texts",
        return_value=file_texts,
    ):
        with patch(
            "ingestion.codebase_ingestion.process_repo_file_texts",
            return_value=chunks,
        ):
            with patch("ingestion.codebase_ingestion.save_chunks_to_mongodb") as fake_save:
                result = ingest_github_codebase(
                    fake_client,
                    "octo/demo",
                    "main",
                    save_to_db=True,
                )

    fake_save.assert_called_once_with(chunks)

    assert result == {
        "repo_full_name": "octo/demo",
        "ref": "main",
        "files_ingested": 1,
        "chunks_created": 1,
        "saved_to_db": True,
        "chunks": chunks,
    }

def test_ingest_github_codebase_does_not_save_chunks_when_disabled() -> None:
    fake_client = object()

    file_texts = [
        {
            "path": "rtl/counter.sv",
            "file_type": "sv",
            "text": "module counter; endmodule",
        }
    ]

    chunks = [
        {"chunk_id": "counter_chunk"},
    ]

    with patch(
        "ingestion.codebase_ingestion.fetch_supported_repo_file_texts",
        return_value=file_texts,
    ):
        with patch(
            "ingestion.codebase_ingestion.process_repo_file_texts",
            return_value=chunks,
        ):
            with patch("ingestion.codebase_ingestion.save_chunks_to_mongodb") as fake_save:
                result = ingest_github_codebase(
                    fake_client,
                    "octo/demo",
                    "main",
                    save_to_db=False,
                )

    fake_save.assert_not_called()

    assert result == {
        "repo_full_name": "octo/demo",
        "ref": "main",
        "files_ingested": 1,
        "chunks_created": 1,
        "saved_to_db": False,
        "chunks": chunks,
    }

def test_ingest_github_codebase_with_default_client_uses_gemini_client() -> None:
    fake_client = object()
    expected_result = {"repo_full_name": "octo/demo"}

    with patch("ingestion.codebase_ingestion.get_gemini_client", return_value=fake_client) as fake_get_client:
        with patch("ingestion.codebase_ingestion.ingest_github_codebase", return_value=expected_result) as fake_ingest:
            result = ingest_github_codebase_with_default_client(
                "octo/demo",
                "main",
                save_to_db=False,
            )

    fake_get_client.assert_called_once_with()
    fake_ingest.assert_called_once_with(
        fake_client,
        "octo/demo",
        "main",
        save_to_db=False,
    )
    assert result == expected_result
