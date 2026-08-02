import os
from pathlib import Path
from typing import Dict

# In-memory file content cache to avoid repeated disk reads
_file_content_cache: Dict[str, str] = {}

def invalidate_cache(file_path: Path) -> None:
    """Invalidates the in-memory cache for the given file path."""
    try:
        path_str = str(file_path.resolve())
        _file_content_cache.pop(path_str, None)
    except Exception:
        pass

def read_file_cached(file_path: Path) -> str:
    """Reads a file's content using the in-memory cache when possible."""
    if not file_path.exists():
        return ""
    try:
        path_str = str(file_path.resolve())
        if path_str not in _file_content_cache:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                _file_content_cache[path_str] = f.read()
        return _file_content_cache[path_str]
    except Exception:
        return ""

def read_lines(file_path: Path, start_line: int, end_line: int) -> str:
    """Reads specific lines from a file (1-indexed, inclusive) using cached contents."""
    if not file_path.exists():
        return f"File not found: {file_path}"
    
    try:
        content = read_file_cached(file_path)
        # Handle empty files
        if not content:
            return ""
            
        lines = content.splitlines(keepends=True)
        total_lines = len(lines)
        
        # Convert to 0-indexed bounds
        start_idx = max(0, start_line - 1)
        end_idx = min(total_lines, end_line)
        
        selected_lines = lines[start_idx:end_idx]
        # Return content with line number markers for model context clarity
        formatted_lines = [f"{start_line + i}: {line}" for i, line in enumerate(selected_lines)]
        return "".join(formatted_lines)
    except Exception as e:
        return f"Error reading file {file_path}: {str(e)}"

def write_file(file_path: Path, content: str) -> None:
    """Writes content to a file, creating parent directories and invalidating cache."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    invalidate_cache(file_path)

def adjust_indentation(replace_block: str, reference_indent: str) -> str:
    """Aligns the indentation of a replacement block to match the reference indentation."""
    lines = replace_block.splitlines()
    if not lines:
        return replace_block
        
    # Find minimum indentation of non-empty lines in replace_block
    non_empty_indents = []
    for line in lines:
        if line.strip():
            non_empty_indents.append(len(line) - len(line.lstrip()))
            
    min_indent = min(non_empty_indents) if non_empty_indents else 0
    
    adjusted_lines = []
    for line in lines:
        if not line.strip():
            adjusted_lines.append("")
        else:
            line_indent = len(line) - len(line.lstrip())
            relative_indent = line_indent - min_indent
            new_indent = reference_indent + (" " * relative_indent)
            adjusted_lines.append(new_indent + line.lstrip())
            
    return "\n".join(adjusted_lines)

def apply_replace(file_path: Path, search_block: str, replace_block: str) -> bool:
    """Finds search_block in a file and replaces it with replace_block.

    3-tier matching strategy — each tier is progressively more lenient but
    has safety guards to prevent false positives that corrupt files:

      Tier 1 – Exact substring match (character-for-character)
      Tier 2 – Indent-agnostic match: strips per-line whitespace.
               Requires ≥2 non-blank lines to prevent single-brace ambiguity.
      Tier 3 – Identifier token-sequence match: extracts word tokens only.
               Requires ≥5 tokens and ≤10 content lines per window.

    Returns True on success, False if not found.
    """
    import re as _re

    if not file_path.exists():
        return False

    try:
        content = read_file_cached(file_path)
        normalized_replace = replace_block.replace('\r\n', '\n')

        # ── Empty file: write directly ──────────────────────────────────────
        if not content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(normalized_replace)
            invalidate_cache(file_path)
            return True

        normalized_content = content.replace('\r\n', '\n')
        normalized_search  = search_block.replace('\r\n', '\n').strip()

        # ── TIER 1: Exact substring ─────────────────────────────────────────
        if normalized_search in normalized_content:
            new_content = normalized_content.replace(normalized_search, normalized_replace, 1)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            invalidate_cache(file_path)
            return True

        content_lines = normalized_content.split('\n')

        # ── TIER 2: Indent-agnostic line-by-line ───────────────────────────
        s_stripped = [l.strip() for l in normalized_search.split('\n')]
        while s_stripped and s_stripped[0] == '':
            s_stripped.pop(0)
        while s_stripped and s_stripped[-1] == '':
            s_stripped.pop()

        # Safety guard: require at least 2 non-blank lines.
        # A single structural line like "}" is too ambiguous to match safely.
        non_blank_search = [l for l in s_stripped if l]
        tier2_eligible = len(non_blank_search) >= 2

        def _lines_match(s_line: str, c_line: str, is_last: bool = False) -> bool:
            """Strict line match. On the last search line, allows a trailing suffix
            (e.g. the file has '}, { timestamps: true }' but search ends with '}')."""
            if s_line == c_line:
                return True
            # Both purely structural (only closing brackets/punctuation)
            is_struct = lambda t: bool(t) and all(ch in '})];,' for ch in t)
            if is_struct(s_line) and is_struct(c_line):
                return True
            # Last-line suffix allowance: file line starts with the search line
            if is_last and c_line.startswith(s_line):
                return True
            return False

        match_idx    = -1
        matched_span = 0

        if tier2_eligible:
            n_s = len(s_stripped)
            for i in range(len(content_lines)):
                s_ptr = 0
                c_ptr = i
                while s_ptr < n_s and c_ptr < len(content_lines):
                    c_line = content_lines[c_ptr].strip()
                    # Skip blank content lines when search expects non-blank
                    if c_line == '' and s_stripped[s_ptr] != '':
                        c_ptr += 1
                        continue
                    is_last_token = (s_ptr == n_s - 1)
                    if _lines_match(s_stripped[s_ptr], c_line, is_last=is_last_token):
                        s_ptr += 1
                        c_ptr += 1
                    else:
                        break
                if s_ptr == n_s:
                    match_idx    = i
                    matched_span = c_ptr - i
                    break

        # ── TIER 3: Identifier token-sequence ──────────────────────────────
        # Only runs when Tier 1 & 2 both failed.
        # Requires ≥5 identifier tokens (avoids short generic matches).
        # Window is capped at 10 content lines (avoids oversized replacements).
        if match_idx == -1:
            def _id_tokens(text: str) -> list:
                return _re.findall(r'[A-Za-z_$][A-Za-z0-9_$]*|[0-9]+', text)

            search_tokens = _id_tokens(normalized_search)
            MAX_WINDOW    = 10
            MIN_TOKENS    = 5

            if len(search_tokens) >= MIN_TOKENS:
                n_tok = len(search_tokens)
                for i in range(len(content_lines)):
                    window: list = []
                    span = 0
                    for k in range(i, min(i + MAX_WINDOW, len(content_lines))):
                        window.extend(_id_tokens(content_lines[k]))
                        span += 1
                        if len(window) >= n_tok:
                            break
                    if window[:n_tok] == search_tokens:
                        match_idx    = i
                        matched_span = span
                        break

        # ── Apply replacement ───────────────────────────────────────────────
        if match_idx != -1:
            first_line       = content_lines[match_idx]
            ref_indent       = first_line[:len(first_line) - len(first_line.lstrip())]
            adjusted_replace = adjust_indentation(normalized_replace, ref_indent)

            before = content_lines[:match_idx]
            after  = content_lines[match_idx + matched_span:]

            parts = []
            if before:
                parts.append('\n'.join(before))
            parts.append(adjusted_replace)
            if after:
                parts.append('\n'.join(after))
            new_content = '\n'.join(parts)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            invalidate_cache(file_path)
            return True

        return False
    except Exception:
        return False

def create_backup(path: Path) -> Path:
    """Clones the file to path.bak to allow easy rollback."""
    backup_path = path.with_suffix(path.suffix + '.bak')
    try:
        content = read_file_cached(path)
        with open(backup_path, 'w', encoding='utf-8') as dst:
            dst.write(content)
    except Exception as e:
        print(f"[Backup] Failed to create backup: {str(e)}")
    return backup_path

def restore_backup(backup_path: Path) -> None:
    """Restores backup file to its original place and deletes backup."""
    if not backup_path.exists():
        return
    
    original_name = backup_path.name
    if original_name.endswith('.bak'):
        original_name = original_name[:-4]
    original_path = backup_path.parent / original_name
    
    try:
        with open(backup_path, 'r', encoding='utf-8', errors='ignore') as src:
            content = src.read()
        with open(original_path, 'w', encoding='utf-8') as dst:
            dst.write(content)
        backup_path.unlink()
        invalidate_cache(original_path)
    except Exception as e:
        print(f"[Backup] Failed to restore backup: {str(e)}")
