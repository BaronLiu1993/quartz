from langchain_openai import ChatOpenAI
from langchain.tools import tool
from openai import BaseModel
from memory import insert_raw_conversation_memory, RawConveresationModel
from pathlib import Path
from langgraph.graph import END, START, MessagesState, StateGraph
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


def _load_system_research_prompt() -> str:
    """Load the plan-agent system prompt from the skills directory."""
    return _RESEARCH_PROMPT_PATH.read_text(encoding="utf-8")


def _load_system_evaluation_prompt() -> str:
    """Load the plan-agent system prompt from the skills directory."""
    return _EVALUATION_PROMPT_PATH.read_text(encoding="utf-8")

def _load_system_synthesis_prompt() -> str:
    """Load the plan-agent system prompt from the skills directory."""
    return _SYNTHESIS_PROMPT_PATH.read_text(encoding="utf-8")


class IntakeStateModel(BaseModel):
    user_id: str
    session_id: str
    code: str
    prompt: str


class ConversationStateModel(BaseModel):
    user_id: str
    session_id: str
    stage: str
    type: str
    raw_conversation: str


class EvaluationModel(BaseModel):
    user_id: str
    session_id: str
    feedback_id: str
    feedback: str
    finished_evaluation: bool

class Step(BaseModel):
    plan_id: str
    step_index: int
    name: str
    description: str

class PlanModel(BaseModel): 
    user_id: str
    session_id: str
    plan: list[Step]

RESEARCH_SYSTEM_PROMPT: str = _load_system_research_prompt()
EVALUATION_SYSTEM_PROMPT: str = _load_system_evaluation_prompt()


def _record_answers(request: ConversationStateModel) -> None:
    insert_raw_conversation_memory(
        RawConveresationModel(
            user_id=request.user_id,
            session_id=request.session_id,
            stage=request.stage,
            type=request.type,
            raw_conversation=request.raw_conversation,
        )
    )

def _planning_orchestration_agent():
    return ChatOpenAI(
        model=MODEL_NAME, max_tokens=MAX_TOKENS, temperature=0.2
    ).with_structured_output()

def _research_agent():
    return ChatOpenAI(
        model=MODEL_NAME, max_tokens=MAX_TOKENS, temperature=0.2
    ).with_structured_output()

def _evaluator_llm():
    return ChatOpenAI(
        model=MODEL_NAME, max_tokens=MAX_TOKENS, temperature=0.2
    ).with_structured_output(EvaluationModel)

tools = []
research_tools_by_name = {tool.name: tool for tool in tools}
research_agent_with_tools = _research_agent.bind_tools(tools)

# Embed each as a 
@tool(parse_docstring=True)
def call_knowledge_semantic_search(query: str) -> str:
    """
    Calls the knowledge semantic search tool to retrieve relevant information for the planning agent.
    """
    pass

def tool_node(state: dict):
    """Performs the tool call"""
    result = []
    _record_answers(ConversationStateModel(
        user_id=state["user_id"],
        session_id=state["session_id"],
        stage=state["stage"],
        type="tool_use",
        raw_conversation=str(state["messages"][-1])
    ))
    for tool_call in state["messages"][-1].tool_calls:
        tool = research_tools_by_name[tool_call["name"]]
        observation = tool.invoke(tool_call["args"])
        result.append(ToolMessage(content=observation, tool_call_id=tool_call["id"]))
    return {"messages": result}

def should_continue_research(state: MessagesState) -> Literal["tool_node", END]:
    """Decide if we should continue the loop or stop based upon whether the LLM made a tool call"""
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tool_node"
    return END


def should_continue_evaluation(state: IntakeStateModel):
    """Decide if we should continue the loop or stop based upon whether the LLM made a tool call"""
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.accept_plan:
        return ""
    return END


def evaluation_node(state: IntakeStateModel) -> dict:
    user_msg = "You are an evaluation agent."
    result: EvaluationModel = _evaluator_llm().invoke(
        [
            SystemMessage(content=EVALUATION_SYSTEM_PROMPT),
            HumanMessage(content=user_msg),
        ]
    )

    return {
        "finished_evaluation": result.finished_evaluation,
        "feedback": result.feedback,
    }

def get_graph():
    agent_builder = StateGraph(MessagesState)

    # Add nodes
    agent_builder.add_node("llm_call", llm_call)
    agent_builder.add_node("tool_node", tool_node)
    agent_builder.add_node("evaluation_node", evaluation_node)

    # Add edges to connect nodes
    agent_builder.add_edge(START, "llm_call")
    agent_builder.add_conditional_edges(
        "llm_call",
        should_continue_research,
        ["tool_node", END]
    )
    agent_builder.add_edge("tool_node", "llm_call")
    agent_builder.add_edge("evaluation_node", "llm_call")
    agent = agent_builder.compile()
    return agent

