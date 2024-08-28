from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
# from django.contrib.auth.models import User

class Page(models.Model):

    # Definitions of this model
    user_id = models.CharField(max_length=255, null=True, blank=True)
    url = models.URLField(unique=False)
    title = models.CharField(max_length=255, null=True, blank=True)
    safe_filename = models.CharField(max_length=255, default='Original file name not available')
    content = models.FileField(null=True, blank=True)
    parent = models.ForeignKey('self', related_name='linked_pages', on_delete=models.CASCADE, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.safe_filename} ({self.url})'

    @classmethod
    def create(cls, user_id, url, title, safe_filename, content, parent):
        page = cls(
            user_id=user_id,
            url=url,
            title=title,
            safe_filename=safe_filename,
            content=content,
            parent=parent
        )
        page.save()
        return page