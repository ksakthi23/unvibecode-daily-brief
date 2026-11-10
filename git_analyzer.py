import ast
import re
import subprocess
from pathlib import Path


def run_git(repo_path, *args):
    result = subprocess.run(
        ["git", "-C", str(repo_path), *args],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    return result.stdout


def redact(line):
    patterns = [
        r'(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*["\']?[^"\'\s,]+["\']?',
        r'\b(?:sk|pk)-[A-Za-z0-9_-]{12,}\b'
    ]

    for pattern in patterns:
        line = re.sub(pattern, "[REDACTED]", line)

    return line.strip()


def find_affected_symbols(file_path, changed_lines):
    try:
        source = Path(file_path).read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (OSError, SyntaxError, UnicodeDecodeError):
        return ["Could not analyse Python syntax"]

    symbols = []

    def visit(node, parents=()):
        if isinstance(node, ast.ClassDef):
            name = ".".join((*parents, node.name))
            symbols.append((node.lineno, node.end_lineno or node.lineno, name))
            parents = (*parents, node.name)

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            name = ".".join((*parents, node.name))
            symbols.append((node.lineno, node.end_lineno or node.lineno, name))
            parents = (*parents, node.name)

        for child in ast.iter_child_nodes(node):
            visit(child, parents)

    visit(tree)

    affected = set()

    for line_number in changed_lines:
        matches = [
            (end - start, name)
            for start, end, name in symbols
            if start <= line_number <= end
        ]

        if matches:
            affected.add(min(matches)[1])
        else:
            affected.add("Module-level code")

    return sorted(affected)


def analyze_repository(repo_path):
    repo_path = Path(repo_path).expanduser().resolve()

    if not repo_path.exists():
        raise FileNotFoundError(f"Repository not found: {repo_path}")

    run_git(repo_path, "rev-parse", "--show-toplevel")

    status = run_git(repo_path, "status", "--short")
    numstat = run_git(repo_path, "diff", "HEAD", "--numstat")
    patch = run_git(
        repo_path, "diff", "HEAD",
        "--no-ext-diff", "--unified=0"
    )

    changed_files = []

    for line in status.splitlines():
        if len(line) >= 4:
            changed_files.append({
                "status": line[:2].strip() or "Modified",
                "file": line[3:]
            })

    added_lines = 0
    removed_lines = 0

    for line in numstat.splitlines():
        parts = line.split("\t", 2)
        if len(parts) == 3:
            try:
                added_lines += int(parts[0])
                removed_lines += int(parts[1])
            except ValueError:
                pass

    details = {}
    current_file = None
    new_line_number = 0
    old_line_number = 0

    for line in patch.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:]
            details.setdefault(
                current_file,
                {
                    "added": [],
                    "removed": [],
                    "added_numbers": [],
                    "removed_numbers": []
                }
            )

        elif line.startswith("@@"):
            old_match = re.search(r"-(\d+)(?:,(\d+))?", line)
            new_match = re.search(r"\+(\d+)(?:,(\d+))?", line)

            if old_match:
                old_line_number = int(old_match.group(1))

            if new_match:
                new_line_number = int(new_match.group(1))

        elif current_file and line.startswith("+") and not line.startswith("+++"):
            details[current_file]["added"].append(redact(line[1:]))
            details[current_file]["added_numbers"].append(new_line_number)
            new_line_number += 1

        elif current_file and line.startswith("-") and not line.startswith("---"):
            details[current_file]["removed"].append(redact(line[1:]))
            details[current_file]["removed_numbers"].append(old_line_number)
            old_line_number += 1

    for item in changed_files:
        filename = item["file"]
        detail = details.get(filename)

        if detail is None:
            continue

        if filename.endswith(".py"):
            detail["affected_symbols_added"] = find_affected_symbols(
                repo_path / filename,
                detail["added_numbers"]
            )

            previous_source = get_previous_file_content(repo_path, filename)

            if previous_source is not None:
                detail["affected_symbols_removed"] = find_symbols_in_source(
                    previous_source,
                    detail["removed_numbers"]
                )
            else:
                detail["affected_symbols_removed"] = []

        else:
            detail["affected_symbols_added"] = []
            detail["affected_symbols_removed"] = []

    return {
        "repository": repo_path.name,
        "path": str(repo_path),
        "changed_files": changed_files,
        "total_files": len(changed_files),
        "added_lines": added_lines,
        "removed_lines": removed_lines,
        "details": details
    }


def get_previous_file_content(repo_path, filename):
    result = subprocess.run(
        ["git", "-C", str(repo_path), "show", f"HEAD:{filename}"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return None

    return result.stdout


def find_symbols_in_source(source, changed_lines):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ["Could not analyse previous Python syntax"]

    symbols = []

    def visit(node, parents=()):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            name = ".".join((*parents, node.name))
            symbols.append((
                node.lineno,
                node.end_lineno or node.lineno,
                name
            ))
            parents = (*parents, node.name)

        for child in ast.iter_child_nodes(node):
            visit(child, parents)

    visit(tree)

    affected = set()

    for line_number in changed_lines:
        matches = [
            (end - start, name)
            for start, end, name in symbols
            if start <= line_number <= end
        ]

        if matches:
            affected.add(min(matches)[1])
        else:
            affected.add("Module-level code")

    return sorted(affected)
