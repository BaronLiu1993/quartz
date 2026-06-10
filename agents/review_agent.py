# Parses Intent and Gather Context on the PR events and Attempts to Get Holistic Perspective on the PR
import logging
from pathlib import Path
from typing import Any, Optional
from pydantic import BaseModel
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langchain.messages import SystemMessage, HumanMessage, ToolMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from .constants import MAX_TOKENS, REVIEW_MODEL_NAME as MODEL_NAME
from memory.conversation_memory import insert_raw_conversation_memory, RawConveresationModel
from service.agent_service import build_pr_context
from memory.embeddings import search_relevant_chunks
from runners.verible_runner import run_lint

def get_review_llm():
    return ChatOpenAI(model=MODEL_NAME, max_tokens=MAX_TOKENS)

_REVIEW_PROMPT_PATH = (
    Path(__file__).resolve().parent.parent / "skills" / "review-agent-001.MD"
)

def _load_system_review_prompt() -> str:
    """Load the review-agent system prompt from the skills directory."""
    return _REVIEW_PROMPT_PATH.read_text(encoding="utf-8")

# Gather context on what to do and what it needs to perform
@tool
def get_pr_history(pr_number: int, repo_full_name: str):
    #by using building pr context function, you get all the information needed from a user and the pr number
    #this below is a docsstring and the function and langchain requires this
    """Fetch stored PR metadata, code diff entries, and review/comment history."""
    return build_pr_context(repo_full_name, pr_number)

@tool
def start_research(pr_number: int, repo_full_name: str, research_focus: Optional[str] = None):
    """Start deeper research for a PR when the review agent needs more context."""
    query = research_focus or f"{repo_full_name} pull request {pr_number}"

    chunks = search_relevant_chunks(query,limit=5)
    
    return {
        "query":query,
        "chunks":chunks
    }

@tool
def execute_simulation(target: str = "rtl/*.v rtl/*.sv"):
    """Run Verible lint on Verilog/SystemVerilog files when execution is needed."""
    return run_lint(target)

REVIEW_TOOLS = [
    get_pr_history, 
    start_research,
    execute_simulation,
    ]

REVIEW_TOOLS_BY_NAME = {}

for review_tools in REVIEW_TOOLS:
    REVIEW_TOOLS_BY_NAME[review_tools.name] = review_tools


def get_review_with_tool():
    return get_review_llm().bind_tools(REVIEW_TOOLS)

def llm_call(state: MessagesState) -> str:
    return {
        "messages": [
            get_review_with_tool().invoke(
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

        if tool_name in REVIEW_TOOLS_BY_NAME:
            tool = REVIEW_TOOLS_BY_NAME[tool_name]
            tool_result= tool.invoke(tool_args)
            result.append(
                ToolMessage(content=str(tool_result),
                            tool_call_id = tool_call["id"],)
                        )
    return { "messages": result}

def continue_researching(state: dict):
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tool_node"
    return END

def get_review_graph():
    graph = StateGraph(MessagesState)

    graph.add_node("llm_call",llm_call)
    graph.add_node("tool_node", tool_node)
    
    graph.add_edge(START,"llm_call")

    graph.add_conditional_edges("llm_call", continue_researching,{"tool_node":"tool_node", END:END,},)

    graph.add_edge("tool_node","llm_call")

    return graph.compile()

def review_pull_request(repo_full_name:str, pr_number:int):
    graph = get_review_graph()

    user_message = HumanMessage(
        content= (
                f"Review pull request {pr_number} in repository {repo_full_name}. "
                "Use get_pr_history to inspect the stored PR context before writing the review."
        )
    )

    review_state = graph.invoke({"messages": [user_message]})
    return extract_final_review_text(review_state)

def extract_final_review_text(review_state:dict) -> str:
    messages = review_state.get("messages", [])
    if not messages:
        return ""
    final_message = messages[-1]
    return final_message.content