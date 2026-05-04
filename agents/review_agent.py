# Parses Intent and Gather Context on the PR events and Attempts to Get Holistic Perspective on the PR
import logging
from pathlib import Path
from typing import Any, Optional
from pydantic import BaseModel
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langchain.messages import SystemMessage, HumanMessage, ToolMessage
from langgraph.graph import END, MessagesState, StateGraph
from .constants import MAX_TOKENS, REVIEW_MODEL_NAME as MODEL_NAME
from memory.conversation_memory import insert_raw_conversation_memory, RawConveresationModel

llm = ChatOpenAI(model=MODEL_NAME, max_tokens=MAX_TOKENS)

_REVIEW_PROMPT_PATH = (
    Path(__file__).resolve().parent.parent / "skills" / "review-agent-001.MD"
)

def _load_system_review_prompt() -> str:
    """Load the review-agent system prompt from the skills directory."""
    return _REVIEW_PROMPT_PATH.read_text(encoding="utf-8")

# Gather context on what to do and what it needs to perform
@tool
def get_pr_history(pr_number: int, repo_full_name: str):
    pass

@tool
def start_research(pr_number: int, repo_full_name: str, research_focus: Optional[str] = None):
    pass

@tool
def execute_simulation():
    pass

tools = [get_pr_history, start_research]
tools_by_name = {tool.name: tool for tool in tools}
llm_with_tools = llm.bind_tools(tools)

def llm_call(state: MessagesState) -> str:
    return {
        "messages": [
            llm_with_tools.invoke(
                [
                    SystemMessage(
                        content=_load_system_review_prompt()
                    )
                ] + 
                state["messages"]
            )
        ]
    }

# Tool Node for calling the tools and getting the results back into the graph
def tool_node(state: dict):
    result = []
    for tool_call in state["messages"][-1].tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        if tool_name in tools_by_name:
            tool_result = tools_by_name[tool_name].invoke(**tool_args)
            result.append(tool_result)
    return { "messages": result}

def continue_researching(state: dict):
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tool_node"
    return END

