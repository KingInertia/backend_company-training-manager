from django.db import models
from django.contrib.auth.models import AbstractUser
from tools.models import TimeStampedModel

class User (AbstractUser, TimeStampedModel):
    image_path = models.ImageField(upload_to='avatars/', blank=True, null=True) 