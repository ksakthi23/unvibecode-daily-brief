import argparse

from git_analyzer import analyze_repository
from brief_generator import generate_brief


def main():
    parser = argparse.ArgumentParser(
        description="UnvibeCode Daily Engineering Brief"
    )
    parser.add_argument("--repo", required=True, help="Git repository path")
    args = parser.parse_args()

    try:
        data = analyze_repository(args.repo)
        brief = generate_brief(data)

        print(brief)

        with open("daily_brief.txt", "w", encoding="utf-8") as file:
            file.write(brief)

        print("\nBrief saved as daily_brief.txt")

    except (RuntimeError, FileNotFoundError) as error:
        print(f"\nError: {error}")


if __name__ == "__main__":
    main()
