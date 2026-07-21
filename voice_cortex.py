import speech_recognition as sr
import pyttsx3
import ollama


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

    except:
        return ""


def ask_cortex(message):

    response = ollama.chat(
        model="hermes3:latest",
        messages=[
            {
                "role": "user",
                "content": message
            }
        ]
    )

    return response["message"]["content"]


while True:

    user = listen()

    if user.lower() == "quit":
        break

    if user:
        answer = ask_cortex(user)
        speak(answer)