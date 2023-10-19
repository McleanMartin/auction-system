from django.db import models
from django.urls import reverse
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    has_proxy = models.BooleanField(default=False,null=True,blank=True)
    is_seller = models.BooleanField(default=False,null=True,blank=True)
    phonenumber = models.CharField(max_length=50)



