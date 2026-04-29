from langchain_openai import ChatOpenAI
from langchain.tools import tool
from openai import BaseModel
from memory import insert_raw_conversation_memory, RawConveresationModel
from pathlib import Path
from langgraph.graph import END, MessagesState
from langchain.messages import SystemMessage, HumanMessage, ToolMessage
from typing import Literal


MODEL_NAME = "gpt-5.5"
MAX_TOKENS = 2000
_RESEARCH_PROMPT_PATH = (
    Path(__file__).resolve().parent.parent / "skills" / "plan-agent-001.MD"
)
_EVALUATION_PROMPT_PATH = (
    Path(__file__).resolve().parent.parent / "skills" / "evaluation-agent-002.MD"
)
_SYNTHESIS_PROMPT_PATH = (
    Path(__file__).resolve().parent.parent / "skills" / "synthesis-agent-003.MD"
)

def _load