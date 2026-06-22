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
from agents.execution_agent import execute_changed_files, execute_target

class InlineReviewComment(BaseModel):
    path: str
    line: int
    body: str
    start_line: int | None = None
    replacement_code: str | None = None

class PullRequestReview(BaseModel):
    summary: str
    comments: list[InlineReviewComment]


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
def execute_simulation(repo_full_name: Optional[str] = None, pr_number: Optional[int] = None,target: Optional[str] = None):
    """Run HDL lint/analysis when execution is needed."""

    if target:
        return execute_target(target)
    
    if repo_full_name is not None and pr_number is not None:
        context = build_pr_context(repo_full_name,pr_number)
        metadata = context.get("metadata") or {}
        files_changed = metadata.get("files_changed") or []

        return execute_changed_files(files_changed)

    return run_lint("rtl/*.v rtl/*.sv")

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
    return extract_structured_review(review_state)

def extract_final_review_text(review_state:dict) -> str:
    messages = review_state.get("messages", [])
    if not messages:
        return ""
    final_message = messages[-1]
    return final_message.content

def get_verible_lint_targets(files: list[str])-> list[str]:
    targets = []

    for file in files:
        normalized_file = file.lower()
        if normalized_file.endswith('.v') or normalized_file.endswith(".sv"):
            targets.append(file)
    
    return targets

def get_vhdl_lint_targets(files: list[str])-> list[str]:
    targets = []

    for file in files:
        normalized_file = file.lower()
        if normalized_file.endswith(".vhd") or normalized_file.endswith(".vhdl"):
            targets.append(file)
    
    return targets

def extract_structured_review(review_state: dict)->PullRequestReview:
    messages = review_state.get("messages",[])

    if not messages:
        return PullRequestReview(summary="", comments=[])
    
    final_message = messages[-1]

    return PullRequestReview.model_validate_json(final_message.content)

