from pathlib import Path

def read_lines(file_path: Path, start_line: int, end_line: int) -> str:
    """Reads specific lines from a file (1-indexed, inclusive)."""
    if not file_path.exists():
        return f"File not found: {file_path}"
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            
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
    """Writes content to a file, creating parent directories if necessary."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def apply_replace(file_path: Path, search_block: str, replace_block: str) -> bool:
    """Finds the search_block in a file and replaces it with replace_block.
    Returns True if replaced successfully, False if block not found.
    """
    if not file_path.exists():
        return False
        
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        # Normalize line endings to avoid platform mismatch errors
        normalized_content = content.replace('\r\n', '\n')
        normalized_search = search_block.replace('\r\n', '\n').strip()
        normalized_replace = replace_block.replace('\r\n', '\n')

        # Try exact match (stripped search block to be resilient to trailing whitespace)
        if normalized_search in normalized_content:
            new_content = normalized_content.replace(normalized_search, normalized_replace, 1)
            # Write back matching the original format style (we write as normal \n or \r\n depending on platform)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True
            
        # Attempt fallback match by removing leading/trailing spaces on each line of the block
        # to match even if indentation in model output differed slightly.
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
            # We found the block! Replace the range from match_idx to match_idx + len(search_lines)
            before = content_lines[:match_idx]
            after = content_lines[match_idx + len(search_lines):]
            # Join everything back
            new_content = "\n".join(before) + "\n" + normalized_replace + "\n" + "\n".join(after)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True
            
        return False
    except Exception:
        return False

def create_backup(path: Path) -> Path:
    """Clones the file to path.bak to allow easy rollback."""
    backup_path = path.with_suffix(path.suffix + '.bak')
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as src:
            content = src.read()
        with open(backup_path, 'w', encoding='utf-8') as dst:
            dst.write(content)
    except Exception as e:
        print(f"[Backup] Failed to create backup: {str(e)}")
    return backup_path

def restore_backup(backup_path: Path) -> None:
    """Restores backup file to its original place and deletes backup."""
    if not backup_path.exists():
        return
    
    # Original path is backup_path without '.bak' suffix
    # Since path.with_suffix replaces the last suffix, and our backup suffix is suffix + '.bak',
    # we can reconstruct the original path by stripping '.bak' or using the stem.
    # A robust way is to drop the '.bak' from name:
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
    except Exception as e:
        print(f"[Backup] Failed to restore backup: {str(e)}")

