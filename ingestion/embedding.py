from dataclasses import dataclass, asdict
import os
import re

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pymongo import MongoClient

load_dotenv()
SUPPORTED_EXTENSIONS = {".txt", ".md", ".v", ".sv", ".vhd", ".vhdl"}

SV_BLOCKS = {
    "module": "endmodule",
    "interface": "endinterface",
    "package": "endpackage",
    "program": "endprogram",
    "primitive": "endprimitive",
    "class": "endclass",
}

VHDL_BLOCKS = {
    "entity": r"(?im)^\s*entity\s+([A-Za-z_][\w]*)\s+is\b",
    "architecture": r"(?im)^\s*architecture\s+([A-Za-z_][\w]*)\s+of\s+[A-Za-z_][\w]*\s+is\b",
    "package": r"(?im)^\s*package\s+([A-Za-z_][\w]*)\s+is\b",
    "package body": r"(?im)^\s*package\s+body\s+([A-Za-z_][\w]*)\s+is\b",
    "configuration": r"(?im)^\s*configuration\s+([A-Za-z_][\w]*)\s+of\s+[A-Za-z_][\w]*\s+is\b",
}

@dataclass
class SourceDocument:
    source: str
    url: str
    topic: str
    file_type: str
    section_title: str
    text: str


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")
    text = text.strip()
    return text

def find_sv_block_starts(text: str) -> list[tuple[str, int]]:
    pattern = r"(?m)^\s*(module|interface|package|program|primitive|class)\s+([A-Za-z_][\w$]*)"
    matches = re.finditer(pattern, text)

    starts = []

    for match in matches:
        block_types = match.group(1)
        start_index = match.start()
        starts.append((block_types, start_index))

    return starts

def find_sv_block_end(text: str, block_type: str, start_index: int) -> int:
    end_keyword = SV_BLOCKS[block_type]
    end_index = text.find(end_keyword, start_index)

    if end_index == -1:
        return -1

    return end_index + len(end_keyword)

def split_sv_units(text: str) -> list[str]:
    starts = find_sv_block_starts(text)
    units = []
    cursor = 0

    for block_type, start_index in starts:
        if start_index > cursor:
            leading_text = text[cursor:start_index].strip()
            if leading_text:
                units.append(leading_text)

        end_index = find_sv_block_end(text, block_type, start_index)

        if end_index != -1:
            unit_text = text[start_index:end_index].strip()
            units.append(unit_text)
            cursor = end_index

    if cursor < len(text):
        trailing_text = text[cursor:].strip()
        if trailing_text:
            units.append(trailing_text)

    return units

def find_vhdl_block_starts(text: str) -> list[tuple[str, int, str]]:
    starts = []

    for block_type, pattern in VHDL_BLOCKS.items():
        matches = re.finditer(pattern, text)
        for match in matches:
            block_name = match.group(1)
            start_index = match.start()
            starts.append((block_type, start_index, block_name))

    starts.sort(key=lambda item: item[1])
    return starts

def find_vhdl_block_end(text: str, block_type: str, block_name: str, start_index: int) -> int:
    escaped_name = re.escape(block_name)

    if block_type == "package body":
        pattern = rf"(?im)^\s*end\b(?:\s+package\s+body)?(?:\s+{escaped_name})?\s*;"
    else:
        block_type_pattern = re.escape(block_type)
        pattern = rf"(?im)^\s*end\b(?:\s+{block_type_pattern})?(?:\s+{escaped_name})?\s*;"

    match = re.search(pattern, text[start_index:])

    if not match:
        return -1

    return start_index + match.end()

def split_vhdl_units(text: str) -> list[str]:
    starts = find_vhdl_block_starts(text)
    units = []
    cursor = 0

    for block_type, start_index, block_name in starts:
        if start_index > cursor:
            leading_text = text[cursor:start_index].strip()
            if leading_text:
                units.append(leading_text)

        end_index = find_vhdl_block_end(text, block_type, block_name, start_index)

        if end_index != -1:
            unit_text = text[start_index:end_index].strip()
            units.append(unit_text)
            cursor = end_index

    if cursor < len(text):
        trailing_text = text[cursor:].strip()
        if trailing_text:
            units.append(trailing_text)

    return units

@dataclass
class DocumentChunk:
    chunk_id: str
    source: str
    url: str
    topic: str
    file_type: str
    section_title: str
    text: str
    embedding: list[float] | None

def infer_sv_section_title(unit_text: str) -> str:
    first_line = unit_text.splitlines()[0].strip()
    match = re.match(
        r"^(module|interface|package|program|primitive|class)\s+([A-Za-z_][\w$]*)",
        first_line,
    )

    if match:
        return f"{match.group(1)} {match.group(2)}"

    return ""

def infer_vhdl_section_title(unit_text: str) -> str:
    first_line = unit_text.splitlines()[0].strip()
    match = re.match(
        r"(?i)^(entity|architecture|package|configuration)\s+([A-Za-z_][\w]*)",
        first_line,
    )

    package_body_match = re.match(
        r"(?i)^package\s+body\s+([A-Za-z_][\w]*)",
        first_line,
    )

    if package_body_match:
        return f"package body {package_body_match.group(1)}"

    if match:
        return f"{match.group(1).lower()} {match.group(2)}"

    return ""

def build_document(source:str, text:str, file_type:str, topic:str ="", url:str = "", section_title:str ="")-> SourceDocument:
    cleaned_text = clean_text(text)
    
    return SourceDocument(
    source = source,
    url = url,
    topic= topic,
    file_type= file_type,
    section_title= section_title,
    text= cleaned_text,
    )

def process_document(client, source:str, text:str, file_type:str, topic:str ="", url:str = "", section_title = "")-> list[DocumentChunk]:
    doc= build_document(source,text,file_type,topic,url,section_title)
    chunks = chunk_document(doc)
    chunks = deduplicate_chunks(chunks)
    return embed_chunks(client,chunks)


def chunk_document(doc: SourceDocument, chunk_size: int = 500) -> list[DocumentChunk]:
    chunks = []
    text = doc.text

    if doc.file_type in {"sv", "v"}:
        units = split_sv_units(text)

        for index, unit_text in enumerate(units):
            chunk = DocumentChunk(
                chunk_id=f"{doc.source}_chunk_{index}",
                source=doc.source,
                url=doc.url,
                topic=doc.topic,
                file_type=doc.file_type,
                section_title=infer_sv_section_title(unit_text),
                text=unit_text,
                embedding=None,
            )
            chunks.append(chunk)

        return chunks

    if doc.file_type in {"vhd", "vhdl"}:
        units = split_vhdl_units(text)

        for index, unit_text in enumerate(units):
            chunk = DocumentChunk(
                chunk_id=f"{doc.source}_chunk_{index}",
                source=doc.source,
                url=doc.url,
                topic=doc.topic,
                file_type=doc.file_type,
                section_title=infer_vhdl_section_title(unit_text),
                text=unit_text,
                embedding=None,
            )
            chunks.append(chunk)

        return chunks

    for i in range(0, len(text), chunk_size):
        chunk_text = text[i:i + chunk_size]
        chunk_number = i // chunk_size

        chunk = DocumentChunk(
            chunk_id=f"{doc.source}_chunk_{chunk_number}",
            source=doc.source,
            url=doc.url,
            topic=doc.topic,
            file_type=doc.file_type,
            section_title=doc.section_title,
            text=chunk_text,
            embedding=None,
        )
        chunks.append(chunk)
    return chunks

def deduplicate_chunks(chunks: list[DocumentChunk]) -> list[DocumentChunk]:
    unique_chunks = {}

    for chunk in chunks:
        unique_chunks[chunk.chunk_id] = chunk

    return list(unique_chunks.values())

def get_mongo_collection():
    mongo_uri = os.getenv("MONGO_DB_URI_STRING")
    client = MongoClient(mongo_uri)
    return client["hardware_assistant"]["chunks"]

def save_chunks_to_mongodb(chunks: list[DocumentChunk]) -> None:
    collection = get_mongo_collection()
    collection.create_index("chunk_id", unique=True)

    for chunk in chunks:
        chunk_dict = asdict(chunk)
        collection.replace_one(
            {"chunk_id": chunk.chunk_id},
            chunk_dict,
            upsert=True,
        )

def prepare_chunk_text(chunk: DocumentChunk) -> str:
    title = chunk.section_title or chunk.source

    return (
        f"title: {title} | "
        f"source: {chunk.source} | "
        f"topic: {chunk.topic} | "
        f"text: {chunk.text}"
    )

def get_gemini_client():
    client = genai.Client(api_key=os.getenv("Gemini_API_Key"))
    return client


def embed_chunk_text(client, text: str) -> list[float]:
    result = client.models.embed_content(
        model="gemini-embedding-001",
        contents=text,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=768,
        ),
    )

    return result.embeddings[0].values

def embed_chunk(client, chunk: DocumentChunk) -> DocumentChunk:
    prepared_text = prepare_chunk_text(chunk)
    embedding = embed_chunk_text(client, prepared_text)
    chunk.embedding = embedding
    return chunk

def embed_chunks(client, chunks: list[DocumentChunk]) -> list[DocumentChunk]:
    embedded_chunks = []

    for chunk in chunks:
        embedded_chunk = embed_chunk(client, chunk)
        embedded_chunks.append(embedded_chunk)

    return embedded_chunks

