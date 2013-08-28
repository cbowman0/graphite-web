from django.db import models

class Link(models.Model):
    url = models.URLField(unique=True)
    date_submitted = models.DateTimeField(auto_now_add=True)
