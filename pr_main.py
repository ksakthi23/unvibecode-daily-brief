import argparse
import os
from pathlib import Path

from pr_analyzer import analyze_pull_request
from brief_generator import generate_brief


def main():
    parser = argparse.ArgumentParser(
        description="UnvibeCode GitHub PR Engineering Brief"
    )

    parser.add_argument("--repo", default=".")
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)

    args = parser.parse_args()

    try:
        data = analyze_pull_request(
            args.repo,
            args.base,
            args.head
        )

        brief = generate_brief(data)

        print(brief)

        output_file = Path("pr_daily_brief.txt")
        output_file.write_text(brief, encoding="utf-8")

        print("\nBrief saved as pr_daily_brief.txt")

        summary_file = os.environ.get("GITHUB_STEP_SUMMARY")

        if summary_file:
            with open(summary_file, "a", encoding="utf-8") as file:
                file.write("## UnvibeCode Daily Engineering Brief\n\n")
                file.write("```text\n")
                file.write(brief)
                file.write("\n```\n")

            print("GitHub Actions summary published.")

    except (RuntimeError, FileNotFoundError) as error:
        parser.exit(1, f"\nError: {error}\n")


if __name__ == "__main__":
    main()