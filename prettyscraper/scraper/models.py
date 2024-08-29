from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
import json
# from django.contrib.auth.models import User

class Page(models.Model):

    # Definitions of this model
    user_id = models.CharField(max_length=255, null=True, blank=True)
    url = models.URLField(unique=False)
    title = models.CharField(max_length=255, null=True, blank=True)
    safe_filename = models.CharField(max_length=255, default='Original file name not available')
    hrefs=models.TextField(null=True, blank=True)
    content = models.TextField(null=True, blank=True)
    parent_url = models.URLField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.safe_filename} ({self.url})'

    @classmethod
    def create(cls, user_id, url, title, safe_filename, hrefs, content, parent_url):
        page = cls(
            user_id=user_id,
            url=url,
            title=title,
            safe_filename=safe_filename,
            hrefs=json.dumps(hrefs),
            content=content,
            parent_url=parent_url
        )
        page.save()
        page.refresh_from_db()
        return page
    
    def get_all_children(self):
        """
        Recursively retrieves all descendant pages.
        Returns a list of Page instances.
        """
        return list(Page.objects.filter(user_id=self.user_id, parent_url=self.url))