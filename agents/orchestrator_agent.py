# Langchain and LangGraph imports
from pathlib import Path

from langchain_openai import ChatOpenAI
from langchain.tools import tool
from langgraph.graph import END, START, MessagesState, StateGraph
from langchain.messages import SystemMessage, HumanMessage, ToolMessage

from constants import MAX_TOKENS, REVIEW_MODEL_NAME as MODEL_NAME
from openai import BaseModel
from memory.conversation_memory import insert_raw_conversation_memory, RawConveresationModel

llm = ChatOpenAI(model=MODEL_NAME, max_tokens=MAX_TOKENS)

# Given a PR figure out which agent needs to be called
_ORCHESTRATOR_PROMPT_PATH = (
    Path(__file__).resolve().parent.parent / "skills" / "orchestrator-agent-001.MD"
)

def _load_system_orchestrator_prompt() -> str:
    """Load the orchestrator-agent system prompt from the skills directory."""
    return _ORCHESTRATOR_PROMPT_PATH.read_text(encoding="utf-8")

class OrchestratorState(BaseModel):
    execution_agent_needed: bool = False
    plan_agent_needed: bool = False
    review_agent_needed: bool = False

orchestrator = llm.with_structured_output(OrchestratorState)
    
    
