from django.db import models

class Page(models.Model):
    url = models.URLField(unique=False)
    title = models.CharField(max_length=255)
    content = models.FileField(upload_to='folder')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)

class Link(models.Model):
    src = models.ForeignKey(Page, related_name='outgoing_links', on_delete=models.CASCADE)
    dst = models.ForeignKey(Page, related_name='incoming_links', on_delete=models.CASCADE)
    when_scraped = models.DateTimeField(auto_now_add=True)