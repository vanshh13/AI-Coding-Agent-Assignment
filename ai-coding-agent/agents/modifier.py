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
            is_new_file = not file_path.exists()
            
            if is_new_file:
                print(f"[Modifier] File {file_name} does not exist. Creating directories and empty file.")
                try:
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.touch()
                except Exception as e:
                    results.append({
                        "file_path": file_name,
                        "success": False,
                        "explanation": f"Failed to create new file structure: {str(e)}",
                        "error": str(e)
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

            # Create backup before starting edits (only for existing files)
            backup_path = None
            if not is_new_file:
                backup_path = create_backup(file_path)
                
            file_success = True
            error_message = ""
            explanations = []

            for edit in edits:
                search_block = edit.get("search_block", "")
                replace_block = edit.get("replace_block", "")
                explanation = edit.get("explanation", "Modified code block")

                explanations.append(explanation)

                # ── Hallucination guard ──────────────────────────────────────
                # Verify the first non-blank stripped line of the search_block
                # actually exists (stripped) somewhere in the current file.
                # If it doesn't, the LLM hallucinated content from another file.
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as _f:
                    current_lines_stripped = [l.strip() for l in _f.read().splitlines()]

                first_search_line = next(
                    (l.strip() for l in search_block.splitlines() if l.strip()), ""
                )
                if first_search_line and first_search_line not in current_lines_stripped:
                    print(f"[Modifier] WARNING: search_block anchor '{first_search_line[:60]}' "
                          f"not found in {file_name} — skipping hallucinated edit.")
                    continue   # skip this edit, try next one

                # Attempt replace operation
                success = apply_replace(file_path, search_block, replace_block)
                if not success:
                    file_success = False
                    error_message = f"Search block mismatch for block: '{search_block[:50]}...'"
                    print(f"[Modifier] Failed to apply block change in {file_name}: {error_message}")
                    break

                # ── Post-edit syntax validation ─────────────────────────────
                with open(file_path, 'r', encoding='utf-8') as f:
                    updated_content = f.read()

                # Python files: ast.parse
                if file_name.endswith(".py"):
                    try:
                        ast.parse(updated_content)
                    except SyntaxError as se:
                        file_success = False
                        error_message = f"Syntax error introduced: {str(se)}"
                        print(f"[Modifier] Syntax validation failed for {file_name}: {error_message}")
                        break

                # JS/TS files: node --check
                if file_name.endswith((".js", ".ts", ".mjs", ".cjs")):
                    import subprocess
                    try:
                        result = subprocess.run(
                            ["node", "--check", str(file_path)],
                            capture_output=True, text=True, timeout=10
                        )
                        if result.returncode != 0:
                            file_success = False
                            error_message = f"JS syntax error: {result.stderr.strip()[:200]}"
                            print(f"[Modifier] Syntax validation failed for {file_name}: {error_message}")
                            break
                    except Exception:
                        pass  # node not available, skip validation

                # ── Duplicate-content guard ──────────────────────────────────
                # Detect if the edit duplicated large blocks of code.
                # Check: if any 10+ consecutive non-blank lines appear twice,
                # the edit likely corrupted the file with a massive hallucination.
                content_lines = [l.strip() for l in updated_content.splitlines() if l.strip()]
                if len(content_lines) >= 20:
                    window_size = 10
                    seen_windows = set()
                    duplicate_found = False
                    for wi in range(len(content_lines) - window_size + 1):
                        window = tuple(content_lines[wi:wi + window_size])
                        if window in seen_windows:
                            duplicate_found = True
                            break
                        seen_windows.add(window)
                    if duplicate_found:
                        file_success = False
                        error_message = f"Duplicate content block detected after edit — likely LLM hallucination"
                        print(f"[Modifier] {error_message} in {file_name}")
                        break

            # Handle rollback if any block fails
            if not file_success:
                print(f"[Modifier] Rolling back changes for {file_name} due to failure.")
                if is_new_file:
                    if file_path.exists():
                        file_path.unlink()
                else:
                    restore_backup(backup_path)
                results.append({
                    "file_path": file_name,
                    "success": False,
                    "explanation": "; ".join(explanations),
                    "error": error_message
                })
            else:
                # Remove backup if all edits succeed
                if backup_path and backup_path.exists():
                    backup_path.unlink()
                print(f"[Modifier] Successfully modified {file_name}")
                results.append({
                    "file_path": file_name,
                    "success": True,
                    "explanation": "; ".join(explanations),
                    "error": ""
                })

        return results
