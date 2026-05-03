from django.shortcuts import render
from .forms import UploadForm
# Create your views here.

def home(request):
    return render(request, "core/home.html")


def upload(request):
    if request.method == "POST":
        form = UploadForm(request.POST, request.FILES)

        if form.is_valid():
            note = form.save()

            print("Saved:", note.title)

            return render(request, "core/upload.html", {
                "form": UploadForm(),
                "success": "Saved to database"
            })
        print(note.id, note.title)
    else:
        form = UploadForm()

    return render(request, "core/upload.html", {"form": form})