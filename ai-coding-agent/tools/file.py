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
    """Finds the search_block in a file and replaces it with replace_block.
    Returns True if replaced successfully, False if block not found.
    """
    if not file_path.exists():
        return False
        
    try:
        content = read_file_cached(file_path)
        
        # Normalize line endings to avoid platform mismatch errors
        normalized_content = content.replace('\r\n', '\n')
        normalized_search = search_block.replace('\r\n', '\n').strip()
        normalized_replace = replace_block.replace('\r\n', '\n')

        # Try exact match (stripped search block to be resilient to trailing whitespace)
        if normalized_search in normalized_content:
            new_content = normalized_content.replace(normalized_search, normalized_replace, 1)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            invalidate_cache(file_path)
            return True
            
        # Attempt fallback match by removing leading/trailing spaces on each line of the block
        search_lines = [line.strip() for line in normalized_search.split('\n') if line.strip()]
        content_lines = normalized_content.split('\n')
        
        # Look for contiguous match of stripped lines
        match_idx = -1
        for i in range(len(content_lines) - len(search_lines) + 1):
            subset = [content_lines[i + j].strip() for j in range(len(search_lines))]
            if subset == search_lines:
                match_idx = i
                break
                
        if match_idx != -1:
            # Detect reference indentation from the first matched line in the file
            first_matched_line = content_lines[match_idx]
            reference_indent = first_matched_line[:len(first_matched_line) - len(first_matched_line.lstrip())]
            
            # Align replacement block indentation to match
            adjusted_replace = adjust_indentation(normalized_replace, reference_indent)
            
            before = content_lines[:match_idx]
            after = content_lines[match_idx + len(search_lines):]
            new_content = "\n".join(before) + "\n" + adjusted_replace + "\n" + "\n".join(after)
            
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
