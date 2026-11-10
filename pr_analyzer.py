import re
import subprocess
from pathlib import Path

from git_analyzer import redact, find_symbols_in_source


def run_git(repo_path, *args):
    result = subprocess.run(
        ["git", "-C", str(repo_path), *args],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())

    return result.stdout


def get_file_at_ref(repo_path, ref, filename):
    result = subprocess.run(
        ["git", "-C", str(repo_path), "show", f"{ref}:{filename}"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return None

    return result.stdout


def analyze_pull_request(repo_path, base_ref, head_ref):
    repo_path = Path(repo_path).expanduser().resolve()

    if not repo_path.exists():
        raise FileNotFoundError(f"Repository not found: {repo_path}")

    run_git(repo_path, "rev-parse", "--show-toplevel")
    run_git(repo_path, "rev-parse", "--verify", base_ref)
    run_git(repo_path, "rev-parse", "--verify", head_ref)

    name_status = run_git(
        repo_path, "diff", "--name-status",
        base_ref, head_ref
    )

    numstat = run_git(
        repo_path, "diff", "--numstat",
        base_ref, head_ref
    )

    patch = run_git(
        repo_path, "diff", base_ref, head_ref,
        "--no-ext-diff", "--unified=0"
    )

    changed_files = []

    for line in name_status.splitlines():
        parts = line.split("\t")

        if len(parts) >= 2:
            status = parts[0]

            if status.startswith("R") or status.startswith("C"):
                filename = parts[-1]
            else:
                filename = parts[1]

            changed_files.append({
                "status": status,
                "file": filename
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

        elif line.startswith("--- a/") and current_file is None:
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

        elif line.startswith("diff --git "):
            current_file = None

    for item in changed_files:
        filename = item["file"]

        detail = details.setdefault(
            filename,
            {
                "added": [],
                "removed": [],
                "added_numbers": [],
                "removed_numbers": []
            }
        )

        if filename.endswith(".py"):
            current_source = get_file_at_ref(
                repo_path, head_ref, filename
            )

            previous_source = get_file_at_ref(
                repo_path, base_ref, filename
            )

            detail["affected_symbols_added"] = (
                find_symbols_in_source(
                    current_source,
                    detail["added_numbers"]
                )
                if current_source is not None else []
            )

            detail["affected_symbols_removed"] = (
                find_symbols_in_source(
                    previous_source,
                    detail["removed_numbers"]
                )
                if previous_source is not None else []
            )

        else:
            detail["affected_symbols_added"] = []
            detail["affected_symbols_removed"] = []

    return {
        "repository": repo_path.name,
        "path": str(repo_path),
        "base_ref": base_ref,
        "head_ref": head_ref,
        "changed_files": changed_files,
        "total_files": len(changed_files),
        "added_lines": added_lines,
        "removed_lines": removed_lines,
        "details": details
    }
