import sys
from pathlib import Path
from unittest.mock import Mock, patch
from langchain.messages import AIMessage, ToolMessage,HumanMessage
from agents.review_agent import tool_node
from langgraph.graph import END


sys.path.append(str(Path(__file__).resolve().parents[1]))

from agents.review_agent import get_pr_history, continue_researching, get_review_graph, _load_system_review_prompt, review_pull_request, start_research, execute_simulation, REVIEW_TOOLS_BY_NAME, get_verible_lint_targets, get_vhdl_lint_targets

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

def test_review_pull_request_invokes_review_graph()-> None:
    fake_graph = Mock()
    fake_graph.invoke.return_value = {"messages":[
        HumanMessage(content="start"),
        AIMessage(content="final review text"),
    ]
    }

    with patch("agents.review_agent.get_review_graph", return_value=fake_graph):
        result = review_pull_request("baron", 9)

    assert result == "final review text"
    fake_graph.invoke.assert_called_once()

    graph_input = fake_graph.invoke.call_args.args[0]
    first_message = graph_input["messages"][0]

    assert isinstance(first_message, HumanMessage)
    assert "Review pull request 9" in first_message.content
    assert "baron" in first_message.content
    assert "get_pr_history" in first_message.content

def test_load_system_review_prompt_reads_prompt_file()-> None:
    prompt = _load_system_review_prompt()

    assert "HDL pull request review agent" in prompt
    assert "get_pr_history" in prompt
    assert "No blocking issues found." in prompt
    assert "Do not invent files" in prompt
    assert "GitHub PR comment" in prompt
    assert "start_research" in prompt
    assert "project knowledge" in prompt
    assert "lint violations" in prompt


def test_start_research_searches_relevant_chunks() -> None:
    expected_chunks = [
        {
            "chunk_id": "reset",
            "source": "reset-guide.md",
            "text": "Use active-low reset.",
            "score": 0.98,
        }
    ]

    with patch("agents.review_agent.search_relevant_chunks", return_value=expected_chunks) as fake_search:
        result = start_research.invoke(
            {
                "repo_full_name": "baron",
                "pr_number": 9,
                "research_focus": "reset behavior",
            }
        )

    assert result == {
        "query": "reset behavior",
        "chunks": expected_chunks,
    }

    fake_search.assert_called_once_with("reset behavior", limit=5)

def test_execute_simulation_runs_lint()->None:
    expected_result = {
        "stdout":"lint ok",
        "stderr":"",
        "returncode": 0,
    }

    with patch("agents.review_agent.run_lint", return_value= expected_result) as fake_run_lint:
        result = execute_simulation.invoke({})
    
    assert result == expected_result
    fake_run_lint.assert_called_once_with("rtl/*.v rtl/*.sv")

def test_execute_simulation_runs_lint_for_target_file()->None:
    excepted_result = {
        "tool":"verible-verilog-lint",
        "target":"rt1/counter.sv",
        "command":"verible-verilog-lint rt1/counter.sv",
        "stdout":"lint ok",
        "stderr":"",
        "returncode": 0,
        "passed": True,
    }

    with patch("agents.review_agent.run_lint", return_value = excepted_result) as fake_run_lint:
        result = execute_simulation.invoke({"target": "rtl/counter.sv"})
    
    assert result == excepted_result
    fake_run_lint.assert_called_once_with("rtl/counter.sv")



def test_review_tools_include_execute_simulation()->None:
    assert "execute_simulation" in REVIEW_TOOLS_BY_NAME

def test_start_research_returns_best_embedded_context() -> None:
    expected_chunks =[
         {
            "chunk_id": "reset-guide",
            "source": "reset-guide.md",
            "text": "Counters should reset to zero before incrementing.",
            "score": 1.0,
        }
    ]
    
    with patch("agents.review_agent.search_relevant_chunks", return_value=expected_chunks) as fake_search:
        result = start_research.invoke(
            {
                "repo_full_name": "baron",
                "pr_number": 9,
                "research_focus": "reset behavior",
            }
        )

        assert result["query"] == "reset behavior"
        assert result["chunks"] == expected_chunks
        fake_search.assert_called_once_with("reset behavior", limit = 5)

def test_get_verible_lint_targets_keeps_only_verilog_files() -> None:
    files = [
        "rtl/counter.sv",
        "rtl/adder.v",
        "docs/readme.md",
        "rtl/package.vhd",
    ]

    result = get_verible_lint_targets(files)

    assert result == [
        "rtl/counter.sv",
        "rtl/adder.v",
    ]

def test_execute_simulation_lints_changed_pr_verilog_files() -> None:
    fake_context = {
        "metadata": {
            "files_changed": [
                "rtl/counter.sv",
                "docs/readme.md",
                "rtl/adder.v",
            ]
        }
    }

    counter_result = {"target": "rtl/counter.sv", "passed": True}
    adder_result = {"target": "rtl/adder.v", "passed": True}

    with patch("agents.review_agent.build_pr_context", return_value=fake_context) as fake_build:
        with patch("agents.review_agent.run_lint", side_effect=[counter_result, adder_result]) as fake_run_lint:
            result = execute_simulation.invoke({
                "repo_full_name": "octo/demo",
                "pr_number": 7,
            })

    fake_build.assert_called_once_with("octo/demo", 7)

    assert fake_run_lint.call_args_list[0].args == ("rtl/counter.sv",)
    assert fake_run_lint.call_args_list[1].args == ("rtl/adder.v",)

    assert result["targets"] == ["rtl/counter.sv", "rtl/adder.v"]
    assert result["results"] == [counter_result, adder_result]
    assert result["passed"] is True

def test_execute_simulation_lints_changed_pr_vhdl_files() -> None:
    fake_context = {
        "metadata": {
            "files_changed": [
                "README.md",
                "rtl/package.vhd",
                "rtl/core.vhdl",
            ]
        }
    }

    package_result = {"target": "rtl/package.vhd", "passed": True}
    core_result = {"target": "rtl/core.vhdl", "passed": True}

    with patch("agents.review_agent.build_pr_context", return_value=fake_context) as fake_build:
        with patch("agents.review_agent.run_vhdl_lint", side_effect=[package_result, core_result]) as fake_run_vhdl_lint:
            result = execute_simulation.invoke({
                "repo_full_name": "octo/demo",
                "pr_number": 7,
            })

    fake_build.assert_called_once_with("octo/demo", 7)

    assert fake_run_vhdl_lint.call_args_list[0].args == ("rtl/package.vhd",)
    assert fake_run_vhdl_lint.call_args_list[1].args == ("rtl/core.vhdl",)

    assert result["targets"] == ["rtl/package.vhd", "rtl/core.vhdl"]
    assert result["results"] == [package_result, core_result]
    assert result["passed"] is True


def test_execute_simulation_returns_message_when_no_hdl_targets() -> None:
    fake_context = {
        "metadata": {
            "files_changed": [
                "README.md",
                "docs/readme.md",
                "scripts/build.py",
            ]
        }
    }

    with patch("agents.review_agent.build_pr_context", return_value=fake_context):
        with patch("agents.review_agent.run_lint") as fake_run_lint:
            with patch("agents.review_agent.run_vhdl_lint") as fake_run_vhdl_lint:
                result = execute_simulation.invoke({
                    "repo_full_name": "octo/demo",
                    "pr_number": 7,
                })

    fake_run_lint.assert_not_called()
    fake_run_vhdl_lint.assert_not_called()

    assert result == {
        "targets": [],
        "results": [],
        "passed": None,
        "message": "No HDL files found for lint.",
    }

def test_get_vhdl_lint_targets_keeps_only_vhdl_files()-> None:
    files = [
        "rtl/counter.sv",
        "rtl/adder.v",
        "rtl/package.vhd",
        "rtl/core.vhdl",
        "rtl/upper.VHDL",
        "docs/readme.md",
    ]

    result = get_vhdl_lint_targets(files)

    assert result == [
        "rtl/package.vhd",
        "rtl/core.vhdl",
        "rtl/upper.VHDL"
    ]

def test_execute_simulation_runs_vhdl_lint_for_target_file()-> None:
    expected_result = {
        "tool": "ghdl",
        "target": "rtl/core.vhdl",
        "command": "ghdl -a rtl/core.vhdl",
        "stdout": "vhdl ok",
        "stderr": "",
        "returncode": 0,
        "passed": True,
    }

    with patch("agents.review_agent.run_vhdl_lint", return_value=expected_result) as fake_run_vdhl_lint:
        result = execute_simulation.invoke({"target": "rtl/core.vhdl"})
    
    assert result == expected_result
    
    fake_run_vdhl_lint.assert_called_once_with("rtl/core.vhdl")


def test_execute_simulation_runs_vhdl_lint_for_uppercase_vhdl_target_file() -> None:
    expected_result = {
        "tool": "ghdl",
        "target": "rtl/core.VHDL",
        "command": "ghdl -a rtl/core.VHDL",
        "stdout": "vhdl ok",
        "stderr": "",
        "returncode": 0,
        "passed": True,
    }

    with patch("agents.review_agent.run_vhdl_lint", return_value=expected_result) as fake_run_vhdl_lint:
        result = execute_simulation.invoke({"target": "rtl/core.VHDL"})

    assert result == expected_result
    fake_run_vhdl_lint.assert_called_once_with("rtl/core.VHDL")

def test_execute_simulation_lints_changed_pr_verilog_and_vhdl_files() -> None:
    fake_context = {
        "metadata": {
            "files_changed": [
                "rtl/counter.sv",
                "rtl/core.vhdl",
                "docs/readme.md",
            ]
        }
    }

    verilog_result = {"target": "rtl/counter.sv", "passed": True}
    vhdl_result = {"target": "rtl/core.vhdl", "passed": True}

    with patch("agents.review_agent.build_pr_context", return_value=fake_context):
        with patch("agents.review_agent.run_lint", return_value=verilog_result) as fake_run_lint:
            with patch("agents.review_agent.run_vhdl_lint", return_value=vhdl_result) as fake_run_vhdl_lint:
                result = execute_simulation.invoke({
                    "repo_full_name": "octo/demo",
                    "pr_number": 7,
                })

    fake_run_lint.assert_called_once_with("rtl/counter.sv")
    fake_run_vhdl_lint.assert_called_once_with("rtl/core.vhdl")

    assert result["targets"] == ["rtl/counter.sv", "rtl/core.vhdl"]
    assert result["results"] == [verilog_result, vhdl_result]
    assert result["passed"] is True
