# UnvibeCode Daily Engineering Brief
![GitHub Actions](https://github.com/ksakthi23/unvibecode-daily-brief/actions/workflows/unvibecode-pr.yml/badge.svg)


**Understand code. Uncover connections. Ship confidently.**

UnvibeCode Daily Engineering Brief is a Python-based code intelligence tool that analyzes Git changes and GitHub Pull Requests to generate clear, structured engineering reports.

It helps developers understand what changed, which Python symbols were affected, and how much code was added or removed.

## Features

- **Git Repository Analysis:** Analyze changes in a local Git repository.
- **Pull Request Analysis:** Compare base and head Git references.
- **Change Detection:** Identify added, modified, deleted, and renamed files.
- **Code Change Statistics:** Calculate added and removed lines.
- **Python Symbol Detection:** Identify affected functions, classes, and other Python symbols using AST analysis.
- **Secret Redaction:** Redact sensitive values from displayed code changes.
- **Engineering Reports:** Generate readable text-based engineering briefs.
- **GitHub Actions Integration:** Automatically generate reports when a Pull Request is opened, updated, or reopened.
- **GitHub Actions Summary:** Publish the generated report in the workflow summary.
- **Artifact Upload:** Save generated reports as downloadable workflow artifacts.

## Technology Stack

| Technology | Purpose |
|---|---|
| Python 3.13 | Core development |
| Git | Repository and change analysis |
| GitHub Actions | Pull Request automation |
| Python AST | Symbol detection |
| Pytest | Automated testing |
| Coverage.py | Statement and branch coverage |

## Project Structure

```text
unvibecode-daily-brief/
│
├── .github/
│   └── workflows/
│       └── unvibecode-pr.yml
│
├── tests/
│   ├── test_git_analyzer.py
│   ├── test_brief_generator.py
│   ├── test_main.py
│   ├── test_pr_analyzer.py
│   └── test_pr_main.py
│
├── git_analyzer.py
├── brief_generator.py
├── main.py
├── pr_analyzer.py
├── pr_main.py
├── requirements.txt
└── README.md
```

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/ksakthi23/unvibecode-daily-brief.git
```

### 2. Navigate to the project

```bash
cd unvibecode-daily-brief
```

### 3. Create a virtual environment

```bash
python3 -m venv .venv
```

### 4. Activate the environment

macOS / Linux:

```bash
source .venv/bin/activate
```

### 5. Install testing dependencies

```bash
python -m pip install pytest pytest-cov
```

**Requirements:** Python 3.13 or compatible Python version and Git.

The application currently uses Python's standard library and does not require additional runtime packages.

## Usage

### Analyze a Git Repository

```bash
python main.py --repo /path/to/your/repository
```

This analyzes the repository and generates:

```text
daily_brief.txt
```

### Analyze a Pull Request

```bash
python pr_main.py --repo . --base BASE_SHA --head HEAD_SHA
```

Replace `BASE_SHA` and `HEAD_SHA` with valid Git commit references.

The tool generates:

```text
pr_daily_brief.txt
```

## GitHub Actions Integration

The project includes an automated GitHub Actions workflow:

`.github/workflows/unvibecode-pr.yml`

The workflow runs when a Pull Request is:

- Opened
- Updated with new commits
- Reopened

It automatically:

1. Checks out the repository.
2. Sets up Python 3.13.
3. Installs project dependencies.
4. Analyzes the Pull Request changes.
5. Generates the engineering brief.
6. Publishes the report in the GitHub Actions summary.
7. Uploads the report as a workflow artifact.

## Testing

Run all automated tests:

```bash
python -m pytest -v
```

Run tests with statement and branch coverage:

```bash
python -m pytest --cov=git_analyzer --cov=brief_generator --cov=main --cov=pr_analyzer --cov=pr_main --cov-branch
```

### Test Results

**Latest verified results:**

| Metric | Result |
|---|---:|
| Total tests | 60 |
| Passed | 60 |
| Failed | 0 |
| Statements covered | 283 / 283 |
| Branches covered | 120 / 120 |
| Statement coverage | 100% |
| Branch coverage | 100% |

## Future Improvements

- Support additional programming languages.
- Add deeper dependency and workflow impact analysis.
- Improve risk identification for code changes.
- Introduce scheduled engineering briefs.
- Expand integrations with developer tools and platforms.

## Author
**Sakthi Krishnakumar**

Aspiring Full-Stack Developer | Python | Generative AI | Software Development

GitHub: https://github.com/ksakthi23

---

*Built as part of the UnvibeCode Engineering Challenge 2026 — Track 2.
