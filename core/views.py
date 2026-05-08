from django.shortcuts import render
from .forms import UploadForm
import pdfplumber
from .models import Note
from django.shortcuts import get_object_or_404
import requests
import google.generativeai as genai
import os
from dotenv import load_dotenv
# Create your views here.

def home(request):
    notes = Note.objects.all().order_by('-id')
    return render(request, "core/home.html",{
        "notes": notes
    })


def upload(request):
    if request.method == "POST":
        form = UploadForm(request.POST, request.FILES)

        if form.is_valid():
            note = form.save()

            # 🔥 Extract text from PDF
            text = ""

            with pdfplumber.open(note.file.path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"

            # Save extracted text
            note.content = text
            note.save()

            print("TEXT LENGTH:", len(text))
            print(text[:200])
            return render(request, "core/upload.html", {
                "form": UploadForm(),
                "success": "PDF processed"
                
            })

    else:
        form = UploadForm()

    return render(request, "core/upload.html", {"form": form})

def note_detail(request, id):
    note = Note.objects.get(id=id)

    answer = ""

    if request.method == "POST":
        question = request.POST.get("question")

        prompt = f"""
        Answer the question ONLY from the provided notes.

        NOTES:
        {note.content}

        QUESTION:
        {question}
        """

        answer = ask_gemini(prompt)

    return render(request, "core/note_detail.html", {
        "note": note,
        "answer": answer
    })

def summarize_text(text):
    url = "http://localhost:11434/api/generate"

    prompt = f"""
Summarize the following content in bullet points.

CONTENT:
{text[:2000]}
"""

    payload = {
        "model": "phi3",
        "prompt": prompt,
        "stream": False
    }

    response = requests.post(url, json=payload)

    data = response.json()

    return data.get("response", "")

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def ask_gemini(prompt):

    response = model.generate_content(prompt)

    return response.text