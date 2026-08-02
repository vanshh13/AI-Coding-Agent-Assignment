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
                # and this duplication wasn't already present in the original file,
                # the edit likely corrupted the file with a massive hallucination.
                content_lines = [l.strip() for l in updated_content.splitlines() if l.strip()]
                original_lines = [l.strip() for l in file_content.splitlines() if l.strip()]
                if len(content_lines) >= 20:
                    window_size = 10
                    seen_windows = set()
                    duplicate_found = False
                    for wi in range(len(content_lines) - window_size + 1):
                        window = tuple(content_lines[wi:wi + window_size])
                        if window in seen_windows:
                            # Verify if this duplication existed in the original file
                            orig_count = sum(
                                1 for oj in range(len(original_lines) - window_size + 1)
                                if tuple(original_lines[oj:oj + window_size]) == window
                            )
                            if orig_count < 2:
                                duplicate_found = True
                                break
                        seen_windows.add(window)
                    if duplicate_found:
                        file_success = False
                        error_message = f"Duplicate content block detected after edit — likely LLM hallucination"
                        print(f"[Modifier] {error_message} in {file_name}")
                        break

            # Attempt fallback if patching failed
            if not file_success:
                print(f"[Modifier] Targeted edits failed for {file_name}: {error_message}. Attempting fallback (rewrite entire file)...")
                # Restore to original state first
                if not is_new_file:
                    restore_backup(backup_path)
                
                # Re-read the file to ensure we are back at the original state
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        file_content = f.read()
                except Exception as e:
                    print(f"[Modifier] Fallback failed: could not re-read original file.")
                    file_content = ""

                if file_content:
                    # Request the LLM to rewrite the entire file
                    fallback_prompt = f"""You are an expert code editor. Your job is to output the ENTIRE updated content of the target file because the previous targeted edits failed with the following error:
{error_message}

User Request:
{request}

Implementation Plan:
{plan_markdown}

Target File Path: {file_name}

Full Content of Target File:
```
{file_content}
```

Please output a JSON object with a single edit that replaces the entire file. The JSON structure must be:
{{
  "edits": [
    {{
      "explanation": "Rewrite entire file to implement the requested changes and ensure syntax correctness.",
      "search_block": <MUST be the entire file content copied exactly from the target file above>,
      "replace_block": <the entire new file content with all modifications incorporated>
    }}
  ]
}}

STRICT RULES:
1. "search_block" MUST be the exact verbatim content of the original file as shown above.
2. "replace_block" MUST be the complete, syntactically correct updated file. Do not truncate or omit any pre-existing code unless requested.
3. Respond ONLY with the JSON object.
"""
                    try:
                        response = llm.call_json(fallback_prompt, system_message="You are a code modifier. Output valid JSON only.")
                        fallback_edits = response.get("edits", [])
                        if fallback_edits:
                            # Re-create backup for fallback attempt
                            if not is_new_file:
                                backup_path = create_backup(file_path)
                            
                            fallback_success = True
                            fallback_error = ""
                            
                            for edit in fallback_edits:
                                s_blk = edit.get("search_block", "")
                                r_blk = edit.get("replace_block", "")
                                
                                success = apply_replace(file_path, s_blk, r_blk)
                                if not success:
                                    # Fallback: if search block mismatch, write replace_block directly
                                    try:
                                        with open(file_path, 'w', encoding='utf-8') as f:
                                            f.write(r_blk)
                                        from tools.file import invalidate_cache
                                        invalidate_cache(file_path)
                                        success = True
                                    except Exception as e:
                                        fallback_success = False
                                        fallback_error = f"Failed to write fallback content directly: {str(e)}"
                                        break
                                
                                # Validate syntax
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    updated_content = f.read()
                                
                                if file_name.endswith(".py"):
                                    try:
                                        ast.parse(updated_content)
                                    except SyntaxError as se:
                                        fallback_success = False
                                        fallback_error = f"Fallback syntax error: {str(se)}"
                                        break
                                
                                if file_name.endswith((".js", ".ts", ".mjs", ".cjs")):
                                    import subprocess
                                    try:
                                        result = subprocess.run(
                                            ["node", "--check", str(file_path)],
                                            capture_output=True, text=True, timeout=10
                                        )
                                        if result.returncode != 0:
                                            fallback_success = False
                                            fallback_error = f"Fallback JS syntax error: {result.stderr.strip()[:200]}"
                                            break
                                    except Exception:
                                        pass
                                
                                # Duplicate guard
                                content_lines = [l.strip() for l in updated_content.splitlines() if l.strip()]
                                original_lines = [l.strip() for l in file_content.splitlines() if l.strip()]
                                if len(content_lines) >= 20:
                                    window_size = 10
                                    seen_windows = set()
                                    dup_found = False
                                    for wi in range(len(content_lines) - window_size + 1):
                                        window = tuple(content_lines[wi:wi + window_size])
                                        if window in seen_windows:
                                            orig_count = sum(
                                                1 for oj in range(len(original_lines) - window_size + 1)
                                                if tuple(original_lines[oj:oj + window_size]) == window
                                            )
                                            if orig_count < 2:
                                                dup_found = True
                                                break
                                        seen_windows.add(window)
                                    if dup_found:
                                        fallback_success = False
                                        fallback_error = "Fallback duplicate content block detected"
                                        break
                            
                            if fallback_success:
                                print(f"[Modifier] Fallback succeeded! Successfully updated {file_name} by rewriting.")
                                file_success = True
                                error_message = ""
                            else:
                                print(f"[Modifier] Fallback failed: {fallback_error}")
                                error_message = fallback_error
                        else:
                            print("[Modifier] Fallback failed: No edits returned.")
                    except Exception as e:
                        print(f"[Modifier] Exception during fallback: {str(e)}")

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
