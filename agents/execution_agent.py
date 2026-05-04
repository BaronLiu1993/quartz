from langchain_openai import ChatOpenAI
from langchain.tools import tool
from openai import BaseModel
from memory.conversation_memory import insert_raw_conversation_memory, RawConveresationModel
from pathlib import Path
from langgraph.graph import END, MessagesState
from langchain.messages import SystemMessage, HumanMessage, ToolMessage
from typing import Literal

MODEL_NAME = "gpt-5.5"
MAX_TOKENS = 2000
_EXECUTION_PROMPT_PATH = (
    Path(__file__).resolve().parent.parent / "skills" / "execution-agent-004.MD"
)

def _execute_plan():
    pass