# Langchain and LangGraph imports
from pathlib import Path

from langchain_openai import ChatOpenAI
from langchain.tools import tool
from langgraph.graph import END, START, MessagesState, StateGraph
from langchain.messages import SystemMessage, HumanMessage, ToolMessage

from .constants import MAX_TOKENS, REVIEW_MODEL_NAME as MODEL_NAME
from pydantic import BaseModel
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
    review_agent_needed: bool = False
    execution_agent_needed: bool = False
    codebase_context_needed: bool = False
    reason: str = ""

orchestrator = llm.with_structured_output(OrchestratorState)

def decide_pr_workflow(pr_context: dict)-> OrchestratorState:
    user_message = HumanMessage(
        content=(
            "Decide which agents are needed for this pull request.\n\n"
            f"PR context:\n{pr_context}"
        )
    )

    return orchestrator.invoke(
        [
            SystemMessage(content=_load_system_orchestrator_prompt()),
            user_message,
        ]
    )

def build_workflow_steps(decision: OrchestratorState)-> list[str]:
    steps = []

    if decision.codebase_context_needed:
        steps.append("codebase_context")
    
    if decision.execution_agent_needed:
        steps.append("execution")

    if decision.review_agent_needed:
        steps.append("review")

    return steps

def plan_pr_workflow(pr_context: dict)-> dict:
    decision = decide_pr_workflow(pr_context)
    steps = build_workflow_steps(decision)

    return {
        "decision": decision,
        "steps":steps,
    }