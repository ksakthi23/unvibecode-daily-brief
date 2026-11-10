import pytest

import main as app


def sample_data():
    return {
        "repository": "demo-project",
        "total_files": 1,
        "added_lines": 2,
        "removed_lines": 1,
        "changed_files": [
            {"status": "M", "file": "app.py"}
        ],
        "details": {}
    }


def test_main_success_saves_daily_brief(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["main.py", "--repo", "/fake/repo"])

    monkeypatch.setattr(
        app,
        "analyze_repository",
        lambda repo: sample_data()
    )
    monkeypatch.setattr(
        app,
        "generate_brief",
        lambda data: "Test engineering brief"
    )

    app.main()

    output = capsys.readouterr().out
    saved_file = tmp_path / "daily_brief.txt"

    assert "Test engineering brief" in output
    assert "Brief saved as daily_brief.txt" in output
    assert saved_file.exists()
    assert saved_file.read_text(encoding="utf-8") == "Test engineering brief"


def test_main_handles_runtime_error(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["main.py", "--repo", "/fake/repo"])

    def raise_runtime_error(repo):
        raise RuntimeError("Git command failed")

    monkeypatch.setattr(app, "analyze_repository", raise_runtime_error)

    app.main()

    output = capsys.readouterr().out

    assert "Error: Git command failed" in output


def test_main_handles_file_not_found_error(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["main.py", "--repo", "/missing/repo"])

    def raise_file_not_found(repo):
        raise FileNotFoundError("Repository not found")

    monkeypatch.setattr(app, "analyze_repository", raise_file_not_found)

    app.main()

    output = capsys.readouterr().out

    assert "Error: Repository not found" in output


def test_main_handles_file_save_error(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["main.py", "--repo", "/fake/repo"])

    monkeypatch.setattr(
        app,
        "analyze_repository",
        lambda repo: sample_data()
    )
    monkeypatch.setattr(
        app,
        "generate_brief",
        lambda data: "Test engineering brief"
    )

    def raise_save_error(*args, **kwargs):
        raise FileNotFoundError("Unable to save report")

    monkeypatch.setattr("builtins.open", raise_save_error)

    app.main()

    output = capsys.readouterr().out

    assert "Test engineering brief" in output
    assert "Error: Unable to save report" in output


def test_main_requires_repo_argument(monkeypatch):
    monkeypatch.setattr("sys.argv", ["main.py"])

    with pytest.raises(SystemExit) as error:
        app.main()

    assert error.value.code == 2


def test_main_direct_execution_entry_point(tmp_path, monkeypatch, capsys):
    import runpy
    import git_analyzer
    import brief_generator

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["main.py", "--repo", "/fake/repo"])

    monkeypatch.setattr(
        git_analyzer,
        "analyze_repository",
        lambda repo: sample_data()
    )
    monkeypatch.setattr(
        brief_generator,
        "generate_brief",
        lambda data: "Direct execution test"
    )

    runpy.run_module("main", run_name="__main__")

    output = capsys.readouterr().out

    assert "Direct execution test" in output
    assert "Brief saved as daily_brief.txt" in output
    assert (tmp_path / "daily_brief.txt").read_text(
        encoding="utf-8"
    ) == "Direct execution test"
