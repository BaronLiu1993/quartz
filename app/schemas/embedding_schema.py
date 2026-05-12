from pydantic import BaseModel

class ProcessDocumentRequest(BaseModel):
    source:str = ""
    text:str = ""
    file_type: str = ""
    topic:str = ""
    url:str =""
    section_title:str = ""
    save_to_db: bool = True
    return_embeddings: bool = False
