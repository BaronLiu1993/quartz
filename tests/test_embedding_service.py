import sys
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.services.embedding_service import clean_text
from app.services.embedding_service import split_sv_units
from app.services.embedding_service import split_vhdl_units
from app.services.embedding_service import chunk_document
from app.services.embedding_service import SourceDocument
from app.services.embedding_service import build_document
from app.services.embedding_service import DocumentChunk
from app.services.embedding_service import deduplicate_chunks
from app.services.embedding_service import infer_sv_section_title
from app.services.embedding_service import infer_vhdl_section_title
from app.services.embedding_service import get_gemini_client
from app.services.embedding_service import process_document
from app.services.embedding_service import save_chunks_to_mongodb
from app.services.embedding_service import get_mongo_collection



def test_for_clean_txt() -> None:
    input = "\r\nhello\r\nworld\r\n"
    result = clean_text(input)
    assert "hello\nworld" == result

def test_for_split_sv_units()-> None:
    input = clean_text("module counter;\nendmodule")
    result = split_sv_units(input)
    excepted = ["module counter;\nendmodule"]
    assert excepted == result

def test_for_split_vhdl_units()-> None:
    input = clean_text("entity counter is\nport (\n\nclk   : in  std_logic;\nreset : in  std_logic;\nq     : out std_logic\n);\nend entity counter;")
    result = split_vhdl_units(input)
    excepted = ["entity counter is\nport (\n\nclk   : in  std_logic;\nreset : in  std_logic;\nq     : out std_logic\n);\nend entity counter;"]
    assert excepted == result

def test_for_build_document()-> None:
    source= "example.sv"
    url=""
    topic="ingestion"
    file_type="sv"
    section_title=""
    text="`timescale 1ns/1ps\n\nmodule counter;\nendmodule\n\nmodule top;\nendmodule"
        
    result = build_document(source,text,file_type,topic,url,section_title)

    expected_source = "example.sv"
    expected_url = ""
    expected_topic = "ingestion"
    expected_file_type ="sv"
    expected_section_title = ""
    expected_text = "`timescale 1ns/1ps\n\nmodule counter;\nendmodule\n\nmodule top;\nendmodule"
    
    assert expected_source == result.source
    assert expected_url == result.url
    assert expected_topic == result.topic
    assert expected_file_type == result.file_type
    assert expected_section_title == result.section_title
    assert expected_text == result.text


def test_for_chunk_document_sv()-> None:
    doc = SourceDocument(
        source= "example.sv",
        url="",
        topic="ingestion",
        file_type="sv",
        section_title="",
        text="`timescale 1ns/1ps\n\nmodule counter;\nendmodule\n\nmodule top;\nendmodule",
        )
    result = chunk_document(doc)

    expected_chunk_count = 3
    expected_chunk_id_0 = "example.sv_chunk_0"
    expected_chunk_text_0 = "`timescale 1ns/1ps"

    expected_chunk_id_1 = "example.sv_chunk_1"
    expected_chunk_section_title_1 = "module counter"
    expected_chunk_text_1 = "module counter;\nendmodule"

    expected_chunk_id_2 = "example.sv_chunk_2"
    expected_chunk_section_title_2 = "module top"
    expected_chunk_text_2 = "module top;\nendmodule"

    assert len(result) == expected_chunk_count
    assert result[0].chunk_id == expected_chunk_id_0
    assert result[0].text == expected_chunk_text_0
    
    assert result[1].chunk_id ==expected_chunk_id_1
    assert result[1].section_title == expected_chunk_section_title_1
    assert result[1].text == expected_chunk_text_1
        
    assert result[2].chunk_id ==expected_chunk_id_2
    assert result[2].section_title == expected_chunk_section_title_2
    assert result[2].text == expected_chunk_text_2

def test_for_chunk_document_vhdl() -> None:
    doc = SourceDocument(
        source="example.vhd",
        url="",
        topic="ingestion",
        file_type="vhd",
        section_title="",
        text="library ieee;\n\nentity counter is\nend entity counter;\n\narchitecture rtl of counter is\nbegin\nend architecture rtl;",
    )

    result = chunk_document(doc)

    expected_chunk_count = 3

    expected_chunk_id_0 = "example.vhd_chunk_0"
    expected_chunk_text_0 = "library ieee;"

    expected_chunk_id_1 = "example.vhd_chunk_1"
    expected_chunk_section_title_1 = "entity counter"
    expected_chunk_text_1 = "entity counter is\nend entity counter;"

    expected_chunk_id_2 = "example.vhd_chunk_2"
    expected_chunk_section_title_2 = "architecture rtl"
    expected_chunk_text_2 = "architecture rtl of counter is\nbegin\nend architecture rtl;"

    assert len(result) == expected_chunk_count

    assert result[0].chunk_id == expected_chunk_id_0
    assert result[0].text == expected_chunk_text_0

    assert result[1].chunk_id == expected_chunk_id_1
    assert result[1].section_title == expected_chunk_section_title_1
    assert result[1].text == expected_chunk_text_1

    assert result[2].chunk_id == expected_chunk_id_2
    assert result[2].section_title == expected_chunk_section_title_2
    assert result[2].text == expected_chunk_text_2

def test_for_deduplicate_chunks() -> None:
    chunk_1 = DocumentChunk(
        chunk_id="same_id",
        source="example.sv",
        url="",
        topic="ingestion",
        file_type="sv",
        section_title="module counter",
        text="first version",
        embedding=None,
    )

    chunk_2 = DocumentChunk(
        chunk_id="same_id",
        source="example.sv",
        url="",
        topic="ingestion",
        file_type="sv",
        section_title="module counter",
        text="second version",
        embedding=None,
    )

    result = deduplicate_chunks([chunk_1, chunk_2])

    expected_count = 1
    expected_text = "second version"

    assert len(result) == expected_count
    assert result[0].text == expected_text

def test_for_infer_sv_section_title()-> None:
    input = "module counter;\nendmodule"
    result =infer_sv_section_title(input)
    expected = "module counter"
    assert result == expected

def test_for_infer_vhdl_section_title() -> None:
    input_text = "entity counter is\nend entity counter;"
    result = infer_vhdl_section_title(input_text)
    expected = "entity counter"

    assert expected == result

def test_save_chunks_to_mongodb_saves_chunks() -> None:
    chunk = DocumentChunk(
        chunk_id="example.sv_chunk_0",
        source="example.sv",
        url="",
        topic="verilog",
        file_type="sv",
        section_title="module counter",
        text="module counter;\nendmodule",
        embedding=[0.1, 0.2, 0.3],
    )

    fake_collection = Mock()

    with patch("app.services.embedding_service.get_mongo_collection", return_value=fake_collection):
        save_chunks_to_mongodb([chunk])

    fake_collection.create_index.assert_called_once_with("chunk_id", unique=True)
    fake_collection.replace_one.assert_called_once()


def test_process_document_adds_mock_embedding() -> None:
    fake_client = Mock()
    
    with patch("app.services.embedding_service.embed_chunk_text", return_value=[0.1, 0.2, 0.3]):

        result = process_document(
            fake_client,
            source="example.sv",
            text="module counter;\nendmodule",
            file_type="sv",
            topic="verilog",
            url="",
            section_title="",
        )

    assert len(result) > 0
    assert result[0].embedding == [0.1, 0.2, 0.3]

