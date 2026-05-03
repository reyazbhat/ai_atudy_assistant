from django.db import models

# Create your models here.
class Note(models.Model):
    title = models.CharField(max_length=100)
    file = models.FileField(upload_to='notes/')
    content = models.TextField(blank=True)

    def __str__(self):
        return self.title