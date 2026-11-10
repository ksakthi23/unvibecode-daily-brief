import runpy
import sys
from pathlib import Path

import pytest

import pr_main


def test_pr_main_success(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys, "argv",
        ["pr_main.py", "--base", "base", "--head", "head"]
    )
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)

    monkeypatch.setattr(
        pr_main,
        "analyze_pull_request",
        lambda *args: {"repository": "test"}
    )
    monkeypatch.setattr(
        pr_main,
        "generate_brief",
        lambda data: "Test engineering brief"
    )

    pr_main.main()

    assert Path("pr_daily_brief.txt").read_text() == "Test engineering brief"
    assert "Brief saved" in capsys.readouterr().out


def test_pr_main_publishes_github_summary(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)

    summary = tmp_path / "github_summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))

    monkeypatch.setattr(
        sys, "argv",
        ["pr_main.py", "--base", "base", "--head", "head"]
    )
    monkeypatch.setattr(
        pr_main,
        "analyze_pull_request",
        lambda *args: {"repository": "test"}
    )
    monkeypatch.setattr(
        pr_main,
        "generate_brief",
        lambda data: "Test engineering brief"
    )

    pr_main.main()

    content = summary.read_text()

    assert "UnvibeCode Daily Engineering Brief" in content
    assert "Test engineering brief" in content
    assert "GitHub Actions summary published." in capsys.readouterr().out


def test_pr_main_handles_runtime_error(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys, "argv",
        ["pr_main.py", "--base", "base", "--head", "head"]
    )
    monkeypatch.setattr(
        pr_main,
        "analyze_pull_request",
        lambda *args: (_ for _ in ()).throw(RuntimeError("Git error"))
    )

    with pytest.raises(SystemExit) as error:
        pr_main.main()

    assert error.value.code == 1
    assert "Git error" in capsys.readouterr().err


def test_pr_main_handles_missing_file_error(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys, "argv",
        ["pr_main.py", "--base", "base", "--head", "head"]
    )
    monkeypatch.setattr(
        pr_main,
        "analyze_pull_request",
        lambda *args: (_ for _ in ()).throw(FileNotFoundError("Missing file"))
    )

    with pytest.raises(SystemExit) as error:
        pr_main.main()

    assert error.value.code == 1
    assert "Missing file" in capsys.readouterr().err


def test_pr_main_direct_execution(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys, "argv",
        ["pr_main.py", "--base", "base", "--head", "head"]
    )
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)

    monkeypatch.setattr(
        "pr_analyzer.analyze_pull_request",
        lambda *args: {"repository": "test"}
    )
    monkeypatch.setattr(
        "brief_generator.generate_brief",
        lambda data: "Direct execution brief"
    )

    runpy.run_module("pr_main", run_name="__main__")

    assert Path("pr_daily_brief.txt").read_text() == "Direct execution brief"
