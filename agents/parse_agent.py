from pydantic import BaseModel
from typing import Literal
from config import get_openai_client



class CompilationInputModel(BaseModel):
    user_id: str
    session_id: str
    code: str

class DecisionAgentModel(BaseModel):
    decision: Literal['proceed', 'abort']

# Handle lint compilation results and decide whether to proceed or abort


async def read_output_node(request: CompilationInputModel) -> DecisionAgentModel:
    """
    Reads the output and decides whether to 
    proceed or abort based on the compilation result.
    """
    client = get_openai_client()
    completion = client.chat.completions.create(
    model="gpt-5.2",
    messages=[
        {"role": "developer", "content": "Talk like a pirate."},
            {
                "role": "user",
                "content": request.code,
            },
        ],
    )
    return completion.choices[0].message.content



    

    

    