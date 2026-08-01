import ast
from pathlib import Path
from typing import Dict, Any, List
from tools.llm import LLMHelper
from tools.file import apply_replace, create_backup, restore_backup

class Modifier:
    @staticmethod
    def modify(repo_path: Path, plan_details: Dict[str, Any], request: str, llm: LLMHelper) -> List[Dict[str, Any]]:
        """Applies targeted search-and-replace edits based on the execution plan.
        Employs backups and rollbacks to ensure robustness.
        """
        files_to_edit = plan_details.get("files_to_edit", [])
        plan_markdown = plan_details.get("plan_markdown", "")
        
        results = []

        for file_name in files_to_edit:
            file_path = repo_path / file_name
            if not file_path.exists():
                print(f"[Modifier] Warning: File {file_name} does not exist. Skipping.")
                results.append({
                    "file_path": file_name,
                    "success": False,
                    "explanation": "File not found.",
                    "error": "File does not exist in repository."
                })
                continue

            print(f"[Modifier] Modifying file: {file_name}")

            # Read full current file content
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    file_content = f.read()
            except Exception as e:
                results.append({
                    "file_path": file_name,
                    "success": False,
                    "explanation": f"Failed to read file: {str(e)}",
                    "error": str(e)
                })
                continue

            # Render modifier template
            prompt = llm.render_prompt(
                "modifier.txt",
                {
                    "request": request,
                    "plan": plan_markdown,
                    "file_path": file_name,
                    "file_content": file_content
                }
            )

            # Get structured JSON edits
            response = llm.call_json(prompt, system_message="You are a code modifier. Output valid JSON only.")
            edits = response.get("edits", [])

            if not edits:
                print(f"[Modifier] No edits returned for {file_name}.")
                results.append({
                    "file_path": file_name,
                    "success": True,
                    "explanation": "No edits required.",
                    "error": ""
                })
                continue

            # Create backup before starting edits
            backup_path = create_backup(file_path)
            file_success = True
            error_message = ""
            explanations = []

            for edit in edits:
                search_block = edit.get("search_block", "")
                replace_block = edit.get("replace_block", "")
                explanation = edit.get("explanation", "Modified code block")

                explanations.append(explanation)

                # Attempt replace operation
                success = apply_replace(file_path, search_block, replace_block)
                if not success:
                    file_success = False
                    error_message = f"Search block mismatch for block: '{search_block[:50]}...'"
                    print(f"[Modifier] Failed to apply block change in {file_name}: {error_message}")
                    break

                # Validate code syntax (if python file)
                if file_name.endswith(".py"):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            updated_content = f.read()
                        ast.parse(updated_content)
                    except SyntaxError as se:
                        file_success = False
                        error_message = f"Syntax error introduced: {str(se)}"
                        print(f"[Modifier] Syntax validation failed for {file_name}: {error_message}")
                        break

            # Handle rollback if any block fails
            if not file_success:
                print(f"[Modifier] Rolling back changes for {file_name} due to failure.")
                restore_backup(backup_path)
                results.append({
                    "file_path": file_name,
                    "success": False,
                    "explanation": "; ".join(explanations),
                    "error": error_message
                })
            else:
                # Remove backup if all edits succeed
                if backup_path.exists():
                    backup_path.unlink()
                print(f"[Modifier] Successfully modified {file_name}")
                results.append({
                    "file_path": file_name,
                    "success": True,
                    "explanation": "; ".join(explanations),
                    "error": ""
                })

        return results
