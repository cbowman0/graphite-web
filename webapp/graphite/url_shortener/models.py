from django.db import models

class Link(models.Model):
    url = models.URLField(verify_exists=True, unique=True)
    date_submitted = models.DateTimeField(auto_now_add=True)
