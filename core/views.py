from django.shortcuts import render, get_object_or_404, redirect
from .forms import UploadForm
from .models import Note
import pdfplumber
import requests
import re
import os
from dotenv import load_dotenv
from django.contrib.auth.views import LoginView
from django.contrib.auth import logout, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from concurrent.futures import ThreadPoolExecutor

load_dotenv()


# HOME PAGE
@login_required
def home(request):

    notes = Note.objects.filter(user=request.user).order_by('-id')

    return render(request, "core/home.html", {
        "notes": notes
    })


# UPLOAD PDF
@login_required
def upload(request):

    if request.method == "POST":

        form = UploadForm(request.POST, request.FILES)

        if form.is_valid():

            note = form.save(commit=False)

            note.user = request.user

            note.save()

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

            # GENERATE STUDY GUIDE (SUMMARY AND MCQS) IN ONE REQUEST TO AVOID CPU OVERLOAD
            summary, mcqs = generate_study_guide(text[:2000])

            note.content = text
            note.summary = summary
            note.mcqs = mcqs

            note.save()

            return render(request, "core/upload.html", {
                "form": UploadForm(),
                "success": "PDF processed successfully",
                "note": note
            })

    else:
        form = UploadForm()

    return render(request, "core/upload.html", {
        "form": form
    })


# NOTE DETAIL + Q&A
@login_required
def note_detail(request, id):

    note = get_object_or_404(Note, id=id, user=request.user)
    notes = Note.objects.filter(user=request.user).order_by('-id')

    answer = ""
    question = ""

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
        {note.content if note.content else note.summary}

        QUESTION:
        {question}
        """

        answer = ask_ai(prompt)

    return render(request, "core/note_detail.html", {
        "note": note,
        "notes": notes,
        "answer": answer,
        "question": question
    })


# SIGNUP
def signup(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("home")
    else:
        form = UserCreationForm()
    
    return render(request, "core/signup.html", {
        "form": form
    })



# HELPER TO CALL GEMINI API
def ask_gemini(prompt):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not found in environment.")
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }]
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            data = response.json()
            return data['candidates'][0]['content']['parts'][0]['text']
        else:
            print("GEMINI API ERROR status:", response.status_code, response.text)
            return None
    except Exception as e:
        print("GEMINI API EXCEPTION:", e)
        return None


# GENERATE STUDY GUIDE (SUMMARY + MCQS) IN A SINGLE LLM CALL
def generate_study_guide(text):
    prompt = f"""
    You are an AI study assistant.
    Analyze the following study notes and generate two sections:
    1. SUMMARY: A student-friendly summary using bullet points of the most important concepts.
    2. MCQS: Generate 5 multiple-choice questions with options A, B, C, D and the correct answer.

    Format your response exactly as follows:
    [SUMMARY_START]
    (Your bullet-point summary here)
    [SUMMARY_END]

    [MCQS_START]
    (Your 5 multiple choice questions here in this format:)
    1. Question
    A) ...
    B) ...
    C) ...
    D) ...
    Answer: Correct Option
    [MCQS_END]

    NOTES:
    {text}
    """

    # Try Gemini API first
    print("Attempting to generate study guide via Gemini API...")
    response_text = ask_gemini(prompt)

    # Fallback to local Ollama if Gemini key is missing or request fails
    if not response_text:
        print("Falling back to local Ollama for study guide...")
        url = "http://localhost:11434/api/generate"
        payload = {
            "model": "phi3",
            "prompt": prompt,
            "stream": False
        }
        try:
            response = requests.post(url, json=payload, timeout=180)
            data = response.json()
            response_text = data.get("response", "")
        except Exception as e:
            print("STUDY GUIDE GENERATION ERROR (Ollama Fallback):", e)
            return "⚠️ AI summary unavailable", "Unable to generate MCQs."

    if not response_text:
        return "⚠️ AI summary unavailable", "Unable to generate MCQs."

    # Parse using regular expressions
    summary = ""
    summary_match = re.search(r'\[SUMMARY_START\](.*?)\[SUMMARY_END\]', response_text, re.DOTALL)
    if summary_match:
        summary = summary_match.group(1).strip()

    mcqs = ""
    mcqs_match = re.search(r'\[MCQS_START\](.*?)\[MCQS_END\]', response_text, re.DOTALL)
    if mcqs_match:
        mcqs = mcqs_match.group(1).strip()

    # Fallback if tags not found
    if not summary or not mcqs:
        parts = re.split(r'MCQS|MCQs|QUESTIONS|Questions', response_text, flags=re.IGNORECASE)
        if len(parts) >= 2:
            summary = parts[0].replace("[SUMMARY_START]", "").replace("SUMMARY", "").strip()
            mcqs = parts[1].replace("[MCQS_END]", "").strip()
        else:
            summary = response_text
            mcqs = "Unable to generate MCQs."

    return summary, mcqs


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

        response = requests.post(url, json=payload, timeout=60)

        data = response.json()

        return data.get("response", "")

    except Exception as e:

        print("OLLAMA ERROR:", e)

        return "⚠️ AI summary unavailable"


# ASK AI
def ask_ai(prompt):
    # Try Gemini API first
    print("Attempting to ask Gemini API...")
    response_text = ask_gemini(prompt)
    if response_text:
        return response_text

    # Fallback to local Ollama
    print("Falling back to local Ollama for Q&A...")
    url = "http://localhost:11434/api/generate"

    payload = {
        "model": "phi3",
        "prompt": prompt,
        "stream": False
    }

    try:

        response = requests.post(url, json=payload, timeout=60)

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
    Generate 5 multiple choice questions from the notes.

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

        response = requests.post(url, json=payload, timeout=60)

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