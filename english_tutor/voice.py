"""Voice module for the English Tutor Bot.

Handles speech-to-text (listening) and text-to-speech (speaking)
using SpeechRecognition and pyttsx3.
"""

import sys

try:
    import speech_recognition as sr
except ImportError:
    sr = None

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None


class VoiceEngine:
    """Manages voice input (microphone -> text) and output (text -> speech)."""

    def __init__(self, rate=160, volume=0.9):
        """Initialize the voice engine.

        Args:
            rate: Speech rate in words per minute (default 160).
            volume: Speech volume 0.0 to 1.0 (default 0.9).
        """
        self._tts_available = False
        self._stt_available = False
        self._engine = None
        self._recognizer = None
        self._microphone = None

        # Initialize text-to-speech
        if pyttsx3 is not None:
            try:
                self._engine = pyttsx3.init()
                self._engine.setProperty("rate", rate)
                self._engine.setProperty("volume", volume)
                # Try to select an English voice
                voices = self._engine.getProperty("voices")
                for voice in voices:
                    if "english" in voice.name.lower():
                        self._engine.setProperty("voice", voice.id)
                        break
                self._tts_available = True
            except Exception as e:
                print(f"[Voice] TTS initialization failed: {e}")
                self._tts_available = False

        # Initialize speech-to-text
        if sr is not None:
            try:
                self._recognizer = sr.Recognizer()
                self._recognizer.energy_threshold = 300
                self._recognizer.dynamic_energy_threshold = True
                self._recognizer.pause_threshold = 1.5
                self._microphone = sr.Microphone()
                # Quick calibration
                with self._microphone as source:
                    self._recognizer.adjust_for_ambient_noise(source, duration=0.5)
                self._stt_available = True
            except Exception as e:
                print(f"[Voice] STT initialization failed: {e}")
                self._stt_available = False

    @property
    def tts_available(self):
        """Whether text-to-speech is available."""
        return self._tts_available

    @property
    def stt_available(self):
        """Whether speech-to-text is available."""
        return self._stt_available

    def speak(self, text):
        """Speak the given text aloud.

        Falls back to printing if TTS is unavailable.

        Args:
            text: The text to speak.
        """
        if self._tts_available:
            try:
                self._engine.say(text)
                self._engine.runAndWait()
            except Exception:
                # Fallback to print only
                pass

    def listen(self, timeout=8, phrase_time_limit=15):
        """Listen for speech via microphone and return recognized text.

        Args:
            timeout: Max seconds to wait for speech to start.
            phrase_time_limit: Max seconds for the entire phrase.

        Returns:
            Recognized text string, or None if recognition failed.
        """
        if not self._stt_available:
            return None

        try:
            with self._microphone as source:
                audio = self._recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit,
                )
            # Use Google's free speech recognition API
            text = self._recognizer.recognize_google(audio)
            return text
        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            print(f"[Voice] Speech recognition service error: {e}")
            return None
        except Exception:
            return None

    def get_status(self):
        """Return a dict describing available voice capabilities."""
        return {
            "tts_available": self._tts_available,
            "stt_available": self._stt_available,
            "tts_engine": "pyttsx3" if self._tts_available else None,
            "stt_engine": "Google Speech Recognition" if self._stt_available else None,
        }
