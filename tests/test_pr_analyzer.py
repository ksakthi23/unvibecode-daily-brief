from unittest.mock import patch

import subprocess

import pytest

from pr_analyzer import analyze_pull_request, get_file_at_ref

def git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True
    )


@pytest.fixture
def git_repo(tmp_path):
    repo = tmp_path

    git(repo, "init")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "Test User")

    source = repo / "calculator.py"
    source.write_text(
        "def add(a, b):\n"
        "    return a + b\n",
        encoding="utf-8"
    )

    git(repo, "add", ".")
    git(repo, "commit", "-m", "Initial commit")

    base = git(repo, "rev-parse", "HEAD").stdout.strip()

    source.write_text(
        "def add(a, b):\n"
        "    result = a + b\n"
        "    return result\n\n"
        "def multiply(a, b):\n"
        "    return a * b\n",
        encoding="utf-8"
    )

    git(repo, "add", ".")
    git(repo, "commit", "-m", "Update calculator")

    head = git(repo, "rev-parse", "HEAD").stdout.strip()

    return repo, base, head


def test_detects_modified_file_and_line_counts(git_repo):
    repo, base, head = git_repo

    result = analyze_pull_request(repo, base, head)

    assert result["total_files"] == 1
    assert result["changed_files"][0]["file"] == "calculator.py"
    assert result["added_lines"] == 5
    assert result["removed_lines"] == 1


def test_detects_added_python_function(git_repo):
    repo, base, head = git_repo

    result = analyze_pull_request(repo, base, head)

    detail = result["details"]["calculator.py"]

    assert "multiply" in detail["affected_symbols_added"]


def test_invalid_repository_raises_error(tmp_path):
    with pytest.raises(RuntimeError):
        analyze_pull_request(tmp_path, "invalid", "HEAD")


def test_missing_repository_raises_error(tmp_path):
    missing = tmp_path / "missing"

    with pytest.raises(FileNotFoundError):
        analyze_pull_request(missing, "main", "HEAD")
def test_get_file_at_ref_returns_none_for_missing_file(git_repo):
    repo, base, head = git_repo

    result = get_file_at_ref(repo, head, "missing.py")

    assert result is None


def test_binary_file_is_handled(git_repo):
    repo, base, head = git_repo

    binary_file = repo / "sample.bin"
    binary_file.write_bytes(b"\x00\x01\x02\x03")

    git(repo, "add", "sample.bin")
    git(repo, "commit", "-m", "Add binary file")

    new_head = git(repo, "rev-parse", "HEAD").stdout.strip()

    result = analyze_pull_request(repo, head, new_head)

    assert result["total_files"] == 1
    assert result["changed_files"][0]["file"] == "sample.bin"
    assert result["details"]["sample.bin"]["affected_symbols_added"] == []
    assert result["details"]["sample.bin"]["affected_symbols_removed"] == []

def test_detects_renamed_file(git_repo):
    repo, base, head = git_repo

    old_file = repo / "calculator.py"
    new_file = repo / "renamed_calculator.py"

    old_file.rename(new_file)

    git(repo, "add", "-A")
    git(repo, "commit", "-m", "Rename calculator")

    renamed_head = git(repo, "rev-parse", "HEAD").stdout.strip()

    result = analyze_pull_request(repo, head, renamed_head)

    assert result["total_files"] == 1
    assert result["changed_files"][0]["file"] == "renamed_calculator.py"


def test_detects_added_non_python_file(git_repo):
    repo, base, head = git_repo

    readme = repo / "README.txt"
    readme.write_text("Project documentation\n", encoding="utf-8")

    git(repo, "add", "README.txt")
    git(repo, "commit", "-m", "Add documentation")

    new_head = git(repo, "rev-parse", "HEAD").stdout.strip()

    result = analyze_pull_request(repo, head, new_head)

    assert result["changed_files"][0]["file"] == "README.txt"
    assert result["details"]["README.txt"]["affected_symbols_added"] == []


def test_detects_deleted_python_file(git_repo):
    repo, base, head = git_repo

    source = repo / "calculator.py"
    source.unlink()

    git(repo, "add", "-A")
    git(repo, "commit", "-m", "Delete calculator")

    new_head = git(repo, "rev-parse", "HEAD").stdout.strip()

    result = analyze_pull_request(repo, head, new_head)

    assert result["total_files"] == 1
    assert result["changed_files"][0]["file"] == "calculator.py"
    assert result["details"]["calculator.py"]["affected_symbols_added"] == []


def test_ignores_malformed_git_output(tmp_path):
    with patch("pr_analyzer.run_git") as mocked_git:
        mocked_git.side_effect = [
            "/fake/repository\n",
            "base\n",
            "head\n",
            "M\n",
            "malformed\n",
            ""
        ]

        result = analyze_pull_request(tmp_path, "base", "head")

    assert result["changed_files"] == []
    assert result["added_lines"] == 0
    assert result["removed_lines"] == 0


def test_handles_hunk_without_old_line_number(tmp_path):
    with patch("pr_analyzer.run_git") as mocked_git:
        mocked_git.side_effect = [
            "/fake/repository\n",
            "base\n",
            "head\n",
            "M\tREADME.txt\n",
            "1\t0\tREADME.txt\n",
            "--- a/README.txt\n"
            "+++ b/README.txt\n"
            "@@ invalid +1 @@\n"
            "+hello\n"
        ]

        result = analyze_pull_request(tmp_path, "base", "head")

    assert result["details"]["README.txt"]["added"] == ["hello"]


def test_handles_hunk_without_new_line_number(tmp_path):
    with patch("pr_analyzer.run_git") as mocked_git:
        mocked_git.side_effect = [
            "/fake/repository\n",
            "base\n",
            "head\n",
            "M\tREADME.txt\n",
            "0\t1\tREADME.txt\n",
            "--- a/README.txt\n"
            "+++ b/README.txt\n"
            "@@ -1 invalid @@\n"
            "-hello\n"
        ]

        result = analyze_pull_request(tmp_path, "base", "head")

    assert result["details"]["README.txt"]["removed"] == ["hello"]
