# Voice Personal English Tutor Bot

An interactive voice-based English tutor that asks questions across multiple categories, listens to your spoken answers, verifies them, and provides corrections with explanations.

## Features

- **Voice Input**: Speak your answers using your microphone (Google Speech Recognition)
- **Voice Output**: Questions and feedback are read aloud (pyttsx3 TTS engine)
- **Text Fallback**: Works in text-only mode when voice is unavailable
- **7 Categories**: Grammar, Vocabulary, Pronunciation, Sentence Correction, Reading Comprehension, Tenses
- **3 Difficulty Levels**: Easy, Medium, Hard
- **Answer Verification**: Fuzzy matching that accepts multiple correct answer forms
- **Corrections & Explanations**: Detailed explanations for every question
- **Session Scoring**: Track your progress with running scores and a final summary
- **Review Wrong Answers**: See all incorrect answers at the end for study

## Installation

```bash
# Install dependencies
pip install SpeechRecognition pyttsx3 PyAudio colorama

# On Ubuntu/Debian, you may also need:
sudo apt-get install python3-pyaudio portaudio19-dev espeak
```

## Usage

```bash
# Start with voice enabled (default)
python -m english_tutor

# Start in text-only mode (no microphone/speaker needed)
python -m english_tutor --text

# List all available categories
python -m english_tutor --list
```

## How It Works

1. **Select a category** (or choose "All Categories" for a mixed quiz)
2. **Select difficulty** (Easy, Medium, Hard, or All)
3. **Choose how many questions** you want
4. **Answer each question** by speaking or typing
5. **Get instant feedback** -- correct/incorrect with explanations
6. **Review your session** with a detailed score summary

## Categories

| Category | Questions | Description |
|---|---|---|
| Grammar | 10 | Fill-in-the-blank, tense usage, subject-verb agreement |
| Vocabulary | 10 | Synonyms, antonyms, word meanings, idioms |
| Pronunciation | 8 | Syllable counting, silent letters, rhyming |
| Sentence Correction | 8 | Fix grammatically incorrect sentences |
| Reading Comprehension | 6 | Context clues, idiom interpretation |
| Tenses | 8 | Tense conversion, identification, fill-in-the-blank |

## Controls During Quiz

- **Speak or type** your answer
- Type **`s`** to skip a question
- Type **`q`** to quit the current quiz
- Press **Ctrl+C** to exit at any time

## Project Structure

```
english_tutor/
  __init__.py      -- Package init
  __main__.py      -- Entry point (CLI argument parsing)
  questions.py     -- Question bank with 50+ questions across 7 categories
  voice.py         -- Voice engine (STT via SpeechRecognition, TTS via pyttsx3)
  tutor.py         -- Tutor engine (quiz flow, scoring, session management)
```

## Requirements

- Python 3.8+
- SpeechRecognition >= 3.10.0
- pyttsx3 >= 2.90
- PyAudio >= 0.2.13 (for microphone input)
- Internet connection (for Google Speech Recognition API)
- Microphone and speakers (for voice mode)
