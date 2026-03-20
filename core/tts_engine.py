# 250 word ,if can user interrupted ,stop and start,
import pyttsx3
from abc import ABC, abstractmethod


class SpeechEngine(ABC):
    """Role model class -> SpeakEnglish | SpeakKhmer"""
    @abstractmethod
    def speak(self, text):
        pass

class TextToSpeech(SpeechEngine):
    """Speak English only"""
    def __init__(self):
        self.__rate = 120
        self.__voice_id = None

        temp = pyttsx3.init()
        self.__voices = temp.getProperty("voices")
        temp.stop()

    def __build_engine(self):
        engine = pyttsx3.init()
        engine.setProperty("rate", self.__rate)
        if self.__voice_id is not None:
            engine.setProperty("voice", self.__voice_id)
        return engine

    def speak(self, text):
        
        if not text.strip():
            print("No text to speak.")
            return
        try:
            engine = self.__build_engine()
            engine.say(text)
            engine.runAndWait()
            engine.stop()
        except Exception as e:
            print(f"Error during speech: {e}")

"""Test"""
def main():
    try:
        speaker = TextToSpeech()
        print("===== TEXT TO VOICE =====")
        print("Type your text and press Enter to hear it.")
        print("Type 'exit' to quit.\n")

        while True:
            text = input("Enter text: ").strip()

            if text.lower() == "exit":
                print("Program ended.")
                break

            speaker.speak(text)

    except Exception as e:
        print(f"Failed to start the application: {e}")


if __name__ == "__main__":
    main()
