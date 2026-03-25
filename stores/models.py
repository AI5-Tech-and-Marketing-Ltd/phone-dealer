from django.db import models
from django.conf import settings

class Store(models.Model):
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='stores')
    logo = models.ImageField(upload_to='stores/logos/', null=True, blank=True)
    cover_picture = models.ImageField(upload_to='stores/banners/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} {self.id}"
