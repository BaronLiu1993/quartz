from pathlib import Path
from tempfile import TemporaryDirectory

from ingestion.codebase_ingestion import fetch_github_file_text
from agents.execution_agent import execute_target, get_hdl_targets, all_results_passed

def execute_pull_request_files(repo_full_name:str, pr_commit_sha:str, files_changed:list[str]):
    hdl_targets = get_hdl_targets(files_changed)
    
    if not hdl_targets:
        return {
            "targets": [],
            "results": [],
            "passed": None,
            "message": "No HDL targets provided",
        }
    
    with TemporaryDirectory() as temporary_directory:
        results = []
        workspace_path = Path(temporary_directory)

        for target in hdl_targets:
            file_text =fetch_github_file_text(repo_full_name, target, pr_commit_sha)
            local_target = workspace_path/target
            local_target.parent.mkdir(parents=True, exist_ok=True)
            local_target.write_text(file_text, "utf-8")
            lint_result = execute_target(str(local_target))
            lint_result["target"] = target
            results.append(lint_result)
        
    return {
        "targets": hdl_targets,
        "results": results,
        "passed": all_results_passed(results)
    }      
