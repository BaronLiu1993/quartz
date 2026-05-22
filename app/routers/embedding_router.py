from dataclasses import asdict 
from pathlib import Path

from fastapi import APIRouter, HTTPException
from app.schemas.embedding_schema import ProcessDocumentRequest
from app.services.embedding_service import(
    get_gemini_client,
    process_document,
    save_chunks_to_mongodb,
)

router = APIRouter(
    prefix = "/embeddings", #prefix means that every route in this file start with /embedding
    tags = ["embeddings"], # groups these routes nicely in FastApi docs
)

ALLOWED_FILE_TYPES = {"txt", "md", "v", "sv", "vhd", "vhdl"}

def normalize_file_type(file_type: str) -> str:
    normalized_file_type = file_type.strip().lower()
    extension = Path(normalized_file_type).suffix

    if extension:
        return extension.lstrip(".")

    return normalized_file_type.lstrip(".")

@router.post("/process")
def process_and_embed_document(request:ProcessDocumentRequest):
    file_type = normalize_file_type(request.file_type)
    if file_type not in ALLOWED_FILE_TYPES:
        raise HTTPException(status_code=400,detail=f"Unsupported file_type '{request.file_type}'. Use one of: {sorted(ALLOWED_FILE_TYPES)}",)
    
    try:
        client = get_gemini_client()
        chunks= process_document(
            client= client, 
            source= request.source,
            text= request.text, 
            file_type= file_type, 
            topic= request.topic, 
            url= request.url, 
            section_title= request.section_title,
             )
        if request.save_to_db is True:
            save_chunks_to_mongodb(chunks)
        
        response_chunks= []
        
        for chunk in chunks:
            chunk_dict = asdict(chunk)
            embedding_length = len(chunk.embedding) if chunk.embedding is not None else 0

            if not request.return_embeddings:
                chunk_dict.pop("embedding", None)

            chunk_dict["embedding_length"] = embedding_length
            response_chunks.append(chunk_dict)
        
        return {
            "message": "Document processed successfully",
            "chunk_count": len(chunks),
            "saved_to_db": request.save_to_db,
            "chunks": response_chunks,
        }
    
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        )

    
    

        

    
