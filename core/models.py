from django.db import models
from django.contrib.auth.models import User

class Note(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    title = models.CharField(max_length=100)
    file = models.FileField(upload_to='uploads/')
    content = models.TextField(blank=True)
    summary = models.TextField(blank=True)

    mcqs = models.TextField(blank=True)

    def __str__(self):
        return self.title



