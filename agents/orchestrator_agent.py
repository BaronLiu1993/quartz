# Langchain and LangGraph imports
from pathlib import Path

from langchain_openai import ChatOpenAI
from langchain.tools import tool
from langgraph.graph import END, START, MessagesState, StateGraph
from langchain.messages import SystemMessage, HumanMessage, ToolMessage

# Other imports
from openai import BaseModel
from memory.conversation_memory import insert_raw_conversation_memory, RawConveresationModel

_ORCHESTRATOR_PROMPT_PATH = (
    Path(__file__).resolve().parent.parent / "skills" / "orchestrator-agent-001.MD"
)

def _load_system_orchestrator_prompt() -> str:
    """Load the orchestrator-agent system prompt from the skills directory."""
    return _ORCHESTRATOR_PROMPT_PATH.read_text(encoding="utf-8")

class OrchestratorState(BaseModel):
    pass
