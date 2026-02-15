"""Entry point for running the English Tutor Bot.

Usage:
    python -m english_tutor              # Voice mode (default)
    python -m english_tutor --text       # Text-only mode
    python -m english_tutor --help       # Show help
"""

import argparse
import sys

from english_tutor.tutor import EnglishTutor


def main():
    parser = argparse.ArgumentParser(
        description="Voice Personal English Tutor Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m english_tutor              Start with voice enabled
  python -m english_tutor --text       Start in text-only mode
  python -m english_tutor --list       List available categories

Categories:
  Grammar, Vocabulary, Pronunciation, Sentence Correction,
  Reading Comprehension, Tenses
        """,
    )
    parser.add_argument(
        "--text",
        action="store_true",
        help="Run in text-only mode (no voice input/output)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available question categories and exit",
    )

    args = parser.parse_args()

    if args.list:
        from english_tutor.questions import get_categories, CATEGORIES
        print("\nAvailable Categories:")
        print("=" * 40)
        for cat in get_categories():
            questions = CATEGORIES[cat]
            easy = sum(1 for q in questions if q["difficulty"] == "easy")
            medium = sum(1 for q in questions if q["difficulty"] == "medium")
            hard = sum(1 for q in questions if q["difficulty"] == "hard")
            print(f"  {cat}")
            print(f"    Total: {len(questions)} questions "
                  f"(Easy: {easy}, Medium: {medium}, Hard: {hard})")
        print()
        sys.exit(0)

    voice_enabled = not args.text
    tutor = EnglishTutor(voice_enabled=voice_enabled)

    try:
        tutor.run()
    except KeyboardInterrupt:
        print("\n\nSession interrupted.")
        if tutor.session.total_asked > 0:
            print(tutor.session.summary())
        print("Goodbye!")
        sys.exit(0)


if __name__ == "__main__":
    main()
