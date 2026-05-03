from django import forms
from .models import Note

class UploadForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = ['title', 'file']