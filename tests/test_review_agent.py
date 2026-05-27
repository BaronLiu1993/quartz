import sys
from pathlib import Path
from unittest.mock import Mock, patch
from langchain.messages import AIMessage, ToolMessage
from agents.review_agent import tool_node
from langgraph.graph import END


sys.path.append(str(Path(__file__).resolve().parents[1]))

from agents.review_agent import get_pr_history, continue_researching, get_review_graph, _load_system_review_prompt


def test_get_pr_history_returns_built_pr_context() -> None:
    expected_context = {
        "repo_full_name": "baron",
        "pr_number": 9,
        "session_id": "gh:baron#9",
        "metadata": {"title","test"},
        "code_entries": [],
        "response_entries": [],
    }

    with patch("agents.review_agent.build_pr_context", return_value=expected_context) as mock_build:
        #LLM tools calls are done using invoke and it sends arugments as a dictionary-like object
        result = get_pr_history.invoke({
            "repo_full_name": "baron",
            "pr_number": 9,
        })
    
    assert expected_context == result
    mock_build.assert_called_once_with("baron",9)

def test_tool_node_runs_requested_tool_and_returns_tool_message() -> None:
    tool_call = {
        "name": "get_pr_history",
        "args": {
            "repo_full_name": "baron",
            "pr_number": 9,
        },
        "id": "call_123",
        "type": "tool_call",
    }

    state = {
        "messages": [
            AIMessage(content="", tool_calls=[tool_call])
        ]
    }

    expected_context = {
        "repo_full_name": "baron",
        "pr_number": 9,
        "session_id": "gh:baron#9",
        "metadata": {"title": "test"},
        "code_entries": [],
        "response_entries": [],
    }

    fake_tool = Mock()
    fake_tool.invoke.return_value = expected_context

    with patch.dict(
        "agents.review_agent.REVIEW_TOOLS_BY_NAME",
        {"get_pr_history": fake_tool},
        clear=True,
    ):
        result = tool_node(state)

    fake_tool.invoke.assert_called_once_with(
        {
            "repo_full_name": "baron",
            "pr_number": 9,
        }
    )

    assert len(result["messages"]) == 1
    assert isinstance(result["messages"][0], ToolMessage)
    assert result["messages"][0].tool_call_id == "call_123"
    assert "baron" in result["messages"][0].content

def test_continue_researching_routes_to_tool_node_when_tool_calls_exist() -> None:
    tool_call = {
        "name": "get_pr_history",
        "args": {
            "repo_full_name": "baron",
            "pr_number": 9,
        },
        "id": "call_123",
        "type": "tool_call",
    }

    state = {
        "messages": [
            AIMessage(content="", tool_calls=[tool_call])
        ]
    }

    result = continue_researching(state)

    assert result == "tool_node"

def test_continue_researching_ends_when_no_tool_calls_exist() -> None:
    state = {
        "messages": [
            AIMessage(content="Review complete.")
        ]
    }

    result = continue_researching(state)

    assert result == END

def test_get_review_graph_compiles() -> None:
    graph = get_review_graph()

    assert graph is not None

def test_load_system_review_prompt_reads_prompt_file() -> None:
    prompt = _load_system_review_prompt()

    assert "HDL pull request review agent" in prompt
    assert "get_pr_history" in prompt