import subprocess

import pytest

from git_analyzer import (
    analyze_repository,
    find_affected_symbols,
    find_symbols_in_source,
    get_previous_file_content,
    redact,
    run_git,
)


def create_git_repo(path):
    path.mkdir()
    subprocess.run(["git", "init", str(path)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(path), "config", "user.email", "test@example.com"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "config", "user.name", "Test User"],
        check=True,
    )
    return path


def commit_all(path):
    subprocess.run(
        ["git", "-C", str(path), "add", "."],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "commit", "-m", "Initial commit"],
        check=True,
        capture_output=True,
    )


def test_redact_api_key():
    result = redact('api_key="test-secret-value"')
    assert "test-secret-value" not in result
    assert "[REDACTED]" in result


def test_redact_token():
    result = redact("password=my-private-password")
    assert "my-private-password" not in result
    assert "[REDACTED]" in result


def test_redact_secret_pattern():
    result = redact("sk-abcdefghijklmnop")
    assert "sk-abcdefghijklmnop" not in result
    assert "[REDACTED]" in result


def test_redact_normal_text():
    assert redact("return total + tax") == "return total + tax"


def test_find_affected_function(tmp_path):
    file = tmp_path / "sample.py"
    file.write_text("def calculate():\n    return 10\n", encoding="utf-8")

    assert find_affected_symbols(file, [2]) == ["calculate"]


def test_find_affected_class_method(tmp_path):
    file = tmp_path / "sample.py"
    file.write_text(
        "class Calculator:\n"
        "    def add(self):\n"
        "        return 10\n",
        encoding="utf-8",
    )

    assert find_affected_symbols(file, [3]) == ["Calculator.add"]


def test_find_affected_module_level_code(tmp_path):
    file = tmp_path / "sample.py"
    file.write_text("VALUE = 10\n", encoding="utf-8")

    assert find_affected_symbols(file, [1]) == ["Module-level code"]


def test_find_affected_invalid_syntax(tmp_path):
    file = tmp_path / "sample.py"
    file.write_text("def broken(:\n", encoding="utf-8")

    assert find_affected_symbols(file, [1]) == [
        "Could not analyse Python syntax"
    ]


def test_find_affected_missing_file(tmp_path):
    file = tmp_path / "missing.py"

    assert find_affected_symbols(file, [1]) == [
        "Could not analyse Python syntax"
    ]


def test_find_affected_invalid_encoding(tmp_path):
    file = tmp_path / "invalid.py"
    file.write_bytes(b"\xff\xfe\xfa")

    assert find_affected_symbols(file, [1]) == [
        "Could not analyse Python syntax"
    ]


def test_find_symbols_in_previous_source():
    source = "def old_function():\n    return 5\n"

    assert find_symbols_in_source(source, [2]) == ["old_function"]


def test_find_symbols_in_previous_class_method():
    source = (
        "class OldClass:\n"
        "    def old_method(self):\n"
        "        return 5\n"
    )

    assert find_symbols_in_source(source, [3]) == ["OldClass.old_method"]


def test_find_symbols_module_level():
    assert find_symbols_in_source("VALUE = 5\n", [1]) == [
        "Module-level code"
    ]


def test_find_symbols_invalid_previous_source():
    assert find_symbols_in_source("def broken(:\n", [1]) == [
        "Could not analyse previous Python syntax"
    ]


def test_run_git_returns_output(tmp_path):
    repo = create_git_repo(tmp_path / "repo")

    result = run_git(repo, "rev-parse", "--is-inside-work-tree")

    assert result.strip() == "true"


def test_run_git_raises_on_invalid_command(tmp_path):
    repo = create_git_repo(tmp_path / "repo")

    with pytest.raises(RuntimeError):
        run_git(repo, "not-a-real-git-command")


def test_get_previous_file_content(tmp_path):
    repo = create_git_repo(tmp_path / "repo")
    source_file = repo / "sample.py"
    source_file.write_text("VALUE = 1\n", encoding="utf-8")
    commit_all(repo)

    content = get_previous_file_content(repo, "sample.py")

    assert content == "VALUE = 1\n"


def test_get_previous_file_content_missing_file(tmp_path):
    repo = create_git_repo(tmp_path / "repo")
    (repo / "sample.py").write_text("VALUE = 1\n", encoding="utf-8")
    commit_all(repo)

    assert get_previous_file_content(repo, "missing.py") is None


def test_analyze_repository_detects_added_and_removed_lines(tmp_path):
    repo = create_git_repo(tmp_path / "repo")
    source_file = repo / "sample.py"

    source_file.write_text(
        "def calculate():\n"
        "    return 10\n",
        encoding="utf-8",
    )
    commit_all(repo)

    source_file.write_text(
        "def calculate():\n"
        "    return 20\n",
        encoding="utf-8",
    )

    result = analyze_repository(repo)

    assert result["repository"] == "repo"
    assert result["total_files"] == 1
    assert result["added_lines"] == 1
    assert result["removed_lines"] == 1

    detail = result["details"]["sample.py"]
    assert detail["affected_symbols_added"] == ["calculate"]
    assert detail["affected_symbols_removed"] == ["calculate"]
    assert len(detail["added"]) == 1
    assert len(detail["removed"]) == 1


def test_analyze_repository_with_no_changes(tmp_path):
    repo = create_git_repo(tmp_path / "repo")
    (repo / "sample.py").write_text("VALUE = 1\n", encoding="utf-8")
    commit_all(repo)

    result = analyze_repository(repo)

    assert result["changed_files"] == []
    assert result["total_files"] == 0
    assert result["added_lines"] == 0
    assert result["removed_lines"] == 0


def test_analyze_repository_missing_path(tmp_path):
    with pytest.raises(FileNotFoundError):
        analyze_repository(tmp_path / "does-not-exist")


def test_analyze_repository_not_git_repository(tmp_path):
    folder = tmp_path / "not-a-repo"
    folder.mkdir()

    with pytest.raises(RuntimeError):
        analyze_repository(folder)


def test_analyze_repository_handles_malformed_git_output(
    tmp_path, monkeypatch
):
    repo = tmp_path / "fake-repo"
    repo.mkdir()

    def fake_run_git(repo_path, *args):
        if args[0] == "rev-parse":
            return "/fake/repo\n"

        if args[0] == "status":
            return "??\nM  orphan.txt\n M config.ini\n"

        if args[0] == "diff" and "--numstat" in args:
            return "bad\tentry\nx\ty\tconfig.ini\n"

        if args[0] == "diff":
            return (
                "+orphan addition\n"
                "-orphan removal\n"
                "+++ b/config.ini\n"
                "@@ malformed @@\n"
                "+new setting\n"
                "-old setting\n"
            )

        raise AssertionError(f"Unexpected Git command: {args}")

    monkeypatch.setattr("git_analyzer.run_git", fake_run_git)

    result = analyze_repository(repo)

    assert result["total_files"] == 2
    assert result["added_lines"] == 0
    assert result["removed_lines"] == 0

    detail = result["details"]["config.ini"]

    assert detail["added"] == ["new setting"]
    assert detail["removed"] == ["old setting"]
    assert detail["added_numbers"] == [0]
    assert detail["removed_numbers"] == [0]
    assert detail["affected_symbols_added"] == []
    assert detail["affected_symbols_removed"] == []


def test_analyze_repository_new_python_file_has_no_previous_symbols(
    tmp_path, monkeypatch
):
    repo = tmp_path / "new-file-repo"
    repo.mkdir()

    new_file = repo / "new_module.py"
    new_file.write_text("def hello():\n    return 'world'\n", encoding="utf-8")

    def fake_run_git(repo_path, *args):
        if args[0] == "rev-parse":
            return "/fake/repo\n"
        if args[0] == "status":
            return "A  new_module.py\n"
        if args[0] == "diff" and "--numstat" in args:
            return "2\t0\tnew_module.py\n"
        if args[0] == "diff":
            return (
                "+++ b/new_module.py\n"
                "@@ -0,0 +1,2 @@\n"
                "+def hello():\n"
                "+    return 'world'\n"
            )
        raise AssertionError(f"Unexpected Git command: {args}")

    monkeypatch.setattr("git_analyzer.run_git", fake_run_git)
    monkeypatch.setattr(
        "git_analyzer.get_previous_file_content",
        lambda repo_path, filename: None
    )

    result = analyze_repository(repo)

    detail = result["details"]["new_module.py"]

    assert detail["affected_symbols_added"] == ["hello"]
    assert detail["affected_symbols_removed"] == []


def test_redact_removes_closing_double_quote():
    assert redact('api_key="sensitive_value"') == "[REDACTED]"


def test_redact_removes_closing_single_quote():
    assert redact("password='sensitive_value'") == "[REDACTED]"
