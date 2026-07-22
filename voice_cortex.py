import speech_recognition as sr
import pyttsx3
from dotenv import load_dotenv

from cortex_context import ask_cortex_ollama, get_alpaca_context

load_dotenv()

engine = pyttsx3.init()

recognizer = sr.Recognizer()


def speak(text):
    print("Cortex:", text)
    engine.say(text)
    engine.runAndWait()


def listen():

    with sr.Microphone() as source:
        print("Listening...")
        recognizer.adjust_for_ambient_noise(source)

        audio = recognizer.listen(source)

    try:
        text = recognizer.recognize_google(audio)

        print("You:", text)
        return text

    except sr.UnknownValueError:
        print("(didn't catch that)")
        return ""

    except sr.RequestError as e:
        print(f"(speech recognition service error: {e})")
        return ""


def ask_cortex(message):
    return ask_cortex_ollama(message, get_alpaca_context())


print("Cortex voice assistant ready. Say something, or say 'quit' to exit.")
speak("Cortex online. Go ahead.")

while True:

    user = listen()

    if user.lower() in ("quit", "exit", "stop"):
        speak("Goodbye.")
        break

    if user:
        answer = ask_cortex(user)
        speak(answer)
