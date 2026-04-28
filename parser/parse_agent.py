from agents import Agent, Runner
from pydantic import BaseModel
from typing import Literal

class CompilationInputModel(BaseModel):
    user_id: str
    session_id: str
    code: str

class DecisionAgentModel(BaseModel):
    decision: Literal['proceed', 'abort']

parse_decision_agent = Agent(
    name="Decision Agent",
    instructions="Given this input, decide whether to proceed or abort.",
    model="gpt-3.5",
)

async def read_output_node(request: CompilationInputModel) -> DecisionAgentModel:
    """
    Reads the output and decides whether to 
    proceed or abort based on the compilation result.
    """
    result = await Runner.run(parse_decision_agent, request)
    return result.final_output

    

    