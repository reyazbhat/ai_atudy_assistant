from django.shortcuts import render
from .forms import UploadForm
import pdfplumber
from .models import Note

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