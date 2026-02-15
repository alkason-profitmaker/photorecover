"""Tutor engine for the English Tutor Bot.

Orchestrates the quiz flow: category selection, question asking,
answer verification, scoring, and session summary.
"""

import random
import time

from english_tutor.questions import (
    get_categories,
    get_questions,
    check_answer,
)
from english_tutor.voice import VoiceEngine


class TutorSession:
    """Represents a single tutoring session with scoring and history."""

    def __init__(self):
        self.total_asked = 0
        self.correct = 0
        self.incorrect = 0
        self.skipped = 0
        self.history = []  # list of dicts with question, user_answer, correct, explanation

    def record(self, question_text, user_answer, is_correct, explanation):
        """Record a question result."""
        self.total_asked += 1
        if user_answer is None:
            self.skipped += 1
        elif is_correct:
            self.correct += 1
        else:
            self.incorrect += 1

        self.history.append({
            "question": question_text,
            "user_answer": user_answer,
            "correct": is_correct,
            "explanation": explanation,
        })

    @property
    def score_percent(self):
        """Return score as a percentage."""
        answered = self.correct + self.incorrect
        if answered == 0:
            return 0.0
        return (self.correct / answered) * 100

    def summary(self):
        """Return a formatted summary string."""
        lines = []
        lines.append("=" * 50)
        lines.append("         SESSION SUMMARY")
        lines.append("=" * 50)
        lines.append(f"  Total questions:  {self.total_asked}")
        lines.append(f"  Correct answers:  {self.correct}")
        lines.append(f"  Incorrect:        {self.incorrect}")
        lines.append(f"  Skipped:          {self.skipped}")
        lines.append(f"  Score:            {self.score_percent:.0f}%")
        lines.append("=" * 50)

        if self.score_percent >= 90:
            lines.append("  Excellent! You have strong English skills!")
        elif self.score_percent >= 70:
            lines.append("  Good job! Keep practicing to improve further.")
        elif self.score_percent >= 50:
            lines.append("  Not bad! Regular practice will help a lot.")
        else:
            lines.append("  Keep learning! Practice makes perfect.")

        # Show incorrect answers for review
        wrong = [h for h in self.history if not h["correct"] and h["user_answer"] is not None]
        if wrong:
            lines.append("")
            lines.append("  Questions to review:")
            lines.append("-" * 50)
            for i, item in enumerate(wrong, 1):
                lines.append(f"  {i}. {item['question']}")
                lines.append(f"     Your answer: {item['user_answer']}")
                lines.append(f"     Explanation: {item['explanation']}")
                lines.append("")

        return "\n".join(lines)


class EnglishTutor:
    """Main tutor engine that drives the interactive quiz."""

    def __init__(self, voice_enabled=True):
        """Initialize the tutor.

        Args:
            voice_enabled: Whether to enable voice input/output.
        """
        self.voice_enabled = voice_enabled
        self.voice = None
        if voice_enabled:
            self.voice = VoiceEngine()

        self.session = TutorSession()

    def output(self, text, speak=True):
        """Display text and optionally speak it.

        Args:
            text: Text to display/speak.
            speak: Whether to also speak the text (default True).
        """
        print(text)
        if speak and self.voice and self.voice.tts_available:
            self.voice.speak(text)

    def get_voice_input(self):
        """Listen for voice input with fallback to text.

        Returns:
            The user's input as a string.
        """
        if self.voice and self.voice.stt_available:
            self.output("(Listening... speak your answer now)", speak=False)
            result = self.voice.listen()
            if result:
                print(f"  >> Heard: \"{result}\"")
                return result
            else:
                self.output("(Could not understand. Please type your answer instead.)", speak=False)

        # Fallback to text input
        try:
            return input("  Your answer: ").strip()
        except (EOFError, KeyboardInterrupt):
            return None

    def get_text_input(self, prompt="  Your answer: "):
        """Get text-only input.

        Args:
            prompt: The input prompt string.

        Returns:
            The user's typed input, or None on interrupt.
        """
        try:
            return input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            return None

    def select_category(self):
        """Let the user pick a category.

        Returns:
            The selected category name, or None to quit.
        """
        categories = get_categories()

        print("\n" + "=" * 50)
        print("  ENGLISH TUTOR - Select a Category")
        print("=" * 50)
        for i, cat in enumerate(categories, 1):
            print(f"  {i}. {cat}")
        print(f"  {len(categories) + 1}. All Categories (Mixed)")
        print(f"  0. Quit")
        print("=" * 50)

        while True:
            choice = self.get_text_input("  Enter your choice (number): ")
            if choice is None or choice == "0":
                return None

            try:
                idx = int(choice)
                if 1 <= idx <= len(categories):
                    return categories[idx - 1]
                elif idx == len(categories) + 1:
                    return "all"
                else:
                    print("  Invalid choice. Try again.")
            except ValueError:
                # Check if they typed the category name
                for cat in categories:
                    if choice.lower() == cat.lower():
                        return cat
                print("  Please enter a number.")

    def select_difficulty(self):
        """Let the user pick a difficulty level.

        Returns:
            Difficulty string or None for all difficulties.
        """
        print("\n  Select difficulty:")
        print("  1. Easy")
        print("  2. Medium")
        print("  3. Hard")
        print("  4. All difficulties (Mixed)")

        choice = self.get_text_input("  Enter your choice (number): ")
        difficulty_map = {"1": "easy", "2": "medium", "3": "hard"}
        return difficulty_map.get(choice)

    def select_question_count(self):
        """Let the user pick how many questions.

        Returns:
            Number of questions as int.
        """
        choice = self.get_text_input("  How many questions? (default 5): ")
        try:
            count = int(choice)
            return max(1, min(count, 50))
        except (ValueError, TypeError):
            return 5

    def ask_question(self, question_dict, question_num, total):
        """Ask a single question and evaluate the answer.

        Args:
            question_dict: The question data dict.
            question_num: Current question number (1-based).
            total: Total number of questions in this round.
        """
        difficulty_badge = {
            "easy": "[Easy]",
            "medium": "[Medium]",
            "hard": "[Hard]",
        }.get(question_dict["difficulty"], "")

        print(f"\n--- Question {question_num}/{total} {difficulty_badge} ---")
        self.output(question_dict["question"])
        print()

        # Get answer via voice or text
        if self.voice_enabled and self.voice and self.voice.stt_available:
            print("  (Speak your answer, or type 's' to skip, 'q' to quit)")
        else:
            print("  (Type your answer, 's' to skip, 'q' to quit)")

        user_answer = self.get_voice_input() if self.voice_enabled else self.get_text_input()

        if user_answer is None or user_answer.lower() == "q":
            self.session.record(question_dict["question"], None, False, question_dict["explanation"])
            return "quit"

        if user_answer.lower() == "s":
            self.output("  Skipped!")
            self.output(f"  Explanation: {question_dict['explanation']}")
            self.session.record(question_dict["question"], None, False, question_dict["explanation"])
            return "skip"

        # Check the answer
        is_correct, explanation = check_answer(question_dict, user_answer)

        if is_correct:
            self.output("  Correct! Well done!")
            self.output(f"  Explanation: {explanation}")
        else:
            self.output(f"  Not quite right.")
            accepted = question_dict["answers"]
            self.output(f"  Correct answer: {accepted[0]}")
            self.output(f"  Explanation: {explanation}")

        self.session.record(question_dict["question"], user_answer, is_correct, explanation)
        return "answered"

    def run_quiz(self, category, difficulty=None, count=5):
        """Run a quiz round for the given category.

        Args:
            category: Category name or "all" for mixed.
            difficulty: Optional difficulty filter.
            count: Number of questions.
        """
        if category == "all":
            # Gather questions from all categories
            all_questions = []
            for cat in get_categories():
                all_questions.extend(get_questions(cat, difficulty))
            random.shuffle(all_questions)
            questions = all_questions[:count]
            category_label = "All Categories"
        else:
            questions = get_questions(category, difficulty, count)
            category_label = category

        if not questions:
            self.output("No questions found for the selected filters. Try different options.")
            return

        diff_label = f" ({difficulty})" if difficulty else " (all levels)"
        print("\n" + "=" * 50)
        self.output(f"  Starting quiz: {category_label}{diff_label}")
        self.output(f"  Questions: {len(questions)}")
        print("=" * 50)
        self.output("Get ready! Here comes your first question.")
        time.sleep(1)

        for i, q in enumerate(questions, 1):
            result = self.ask_question(q, i, len(questions))
            if result == "quit":
                self.output("\nQuiz ended early.")
                break
            time.sleep(0.5)

    def run(self):
        """Main loop: welcome, category selection, quiz, repeat."""
        print("\n" + "=" * 50)
        print("   VOICE PERSONAL ENGLISH TUTOR")
        print("=" * 50)
        self.output("Welcome to your personal English tutor!")

        # Show voice status
        if self.voice:
            status = self.voice.get_status()
            if status["tts_available"]:
                print("  [Voice Output: ON]")
            else:
                print("  [Voice Output: OFF - pyttsx3 not available]")
            if status["stt_available"]:
                print("  [Voice Input: ON]")
            else:
                print("  [Voice Input: OFF - SpeechRecognition/PyAudio not available]")
        else:
            print("  [Voice: DISABLED - text mode only]")

        self.output("I will ask you English questions and help you learn.")
        self.output("Let's begin!\n")

        while True:
            category = self.select_category()
            if category is None:
                break

            difficulty = self.select_difficulty()
            count = self.select_question_count()

            self.run_quiz(category, difficulty, count)

            # Show running score
            print(f"\n  Running score: {self.session.correct}/{self.session.total_asked} "
                  f"({self.session.score_percent:.0f}%)")

            again = self.get_text_input("\n  Continue with another round? (y/n): ")
            if again is None or again.lower() not in ("y", "yes"):
                break

        # Final summary
        if self.session.total_asked > 0:
            print("\n" + self.session.summary())
            self.output("Thank you for practicing! See you next time.")
        else:
            self.output("Goodbye! Come back soon to practice your English.")
