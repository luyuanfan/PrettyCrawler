from django.db import models
from django.contrib.auth.models import User
# from django.core.files.storage import default_storage, FileSystemStorage

# fs = FileSystemStorage(location='/downloads')

class Page(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    url = models.URLField(unique=False)
    title = models.CharField(max_length=255)
    content = models.FileField()
    uploaded_at = models.DateTimeField(auto_now_add=True)
    parent = models.ForeignKey('self', related_name='linked_pages', on_delete=models.CASCADE)

    def __str__(self):
        return self.title

# class Link(models.Model):
#     src = models.ForeignKey(Page, on_delete=models.CASCADE)
#     dst = models.ForeignKey(Page, on_delete=models.CASCADE)
#     when_scraped = models.DateTimeField(auto_now_add=True)