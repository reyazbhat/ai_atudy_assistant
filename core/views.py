from django.shortcuts import render
from .forms import UploadForm
from .models import Note
import pdfplumber
import requests
import re
from django.contrib.auth.views import LoginView
from django.contrib.auth import logout
from django.shortcuts import redirect


# HOME PAGE
def home(request):

    notes = Note.objects.all().order_by('-id')

    return render(request, "core/home.html", {
        "notes": notes
    })


# UPLOAD PDF
def upload(request):

    if request.method == "POST":

        form = UploadForm(request.POST, request.FILES)

        if form.is_valid():

            note = form.save()

            # EXTRACT TEXT FROM PDF
            text = ""

            with pdfplumber.open(note.file.path) as pdf:

                for page in pdf.pages:

                    page_text = page.extract_text()

                    if page_text:
                        text += page_text + "\n"

            # CLEAN TEXT
            text = clean_text(text)

            print("TEXT LENGTH:", len(text))
            print(text[:500])

            # SUMMARIZE USING OLLAMA
            summary = summarize_text(text[:2000])

            mcqs = generate_mcqs(text[:2000])

            note.content = summary
            note.mcqs = mcqs

            note.save()

            return render(request, "core/upload.html", {
                "form": UploadForm(),
                "success": "PDF processed successfully"
            })

    else:
        form = UploadForm()

    return render(request, "core/upload.html", {
        "form": form
    })


# NOTE DETAIL + Q&A
def note_detail(request, id):

    note = Note.objects.get(id=id)

    answer = ""

    if request.method == "POST":

        question = request.POST.get("question")

        prompt = f"""
        You are an AI study assistant.

        Answer the question from the notes below.

        RULES:
        - Answer clearly
        - Use bullet points if needed
        - Be student friendly
        - Answer only from notes

        NOTES:
        {note.content}

        QUESTION:
        {question}
        """

        answer = ask_ai(prompt)

    return render(request, "core/note_detail.html", {
        "note": note,
        "answer": answer
    })


# SUMMARIZE TEXT
def summarize_text(text):

    prompt = f"""
    Summarize these study notes clearly.

    RULES:
    - Use bullet points
    - Keep important concepts only
    - Remove repeated text
    - Student friendly

    CONTENT:
    {text}
    """

    url = "http://localhost:11434/api/generate"

    payload = {
        "model": "phi3",
        "prompt": prompt,
        "stream": False
    }

    try:

        response = requests.post(url, json=payload)

        data = response.json()

        return data.get("response", "")

    except Exception as e:

        print("OLLAMA ERROR:", e)

        return "⚠️ AI summary unavailable"


# ASK AI
def ask_ai(prompt):

    url = "http://localhost:11434/api/generate"

    payload = {
        "model": "phi3",
        "prompt": prompt,
        "stream": False
    }

    try:

        response = requests.post(url, json=payload)

        data = response.json()

        return data.get("response", "")

    except Exception as e:

        print("OLLAMA ERROR:", e)

        return "⚠️ AI answer unavailable"


# CLEAN TEXT
def clean_text(text):

    text = re.sub(r'\s+', ' ', text)

    text = re.sub(r'[^a-zA-Z0-9.,!?()\-\n ]', '', text)

    return text.strip()

def generate_mcqs(text):

    prompt = f"""
    Generate 10 multiple choice questions from the notes.

    Format:

    1. Question

    A)
    B)
    C)
    D)

    Answer: Correct Option

    NOTES:
    {text}
    """

    url = "http://localhost:11434/api/generate"

    payload = {
        "model": "phi3",
        "prompt": prompt,
        "stream": False
    }

    try:

        response = requests.post(url, json=payload)

        data = response.json()

        return data.get("response", "")

    except Exception as e:

        print("MCQ ERROR:", e)

        return "Unable to generate MCQs."
    

class CustomLoginView(LoginView):
    template_name = "core/login.html"


def logout_view(request):

    logout(request)

    return redirect("login")