from django.conf import settings
from django.db import models

# Create your models here.
from django.contrib.auth.models import User


class Disease(models.Model):
    name = models.CharField(max_length=100)
    date_created = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)

    def __str__(self):
        return self.name


class Symptoms(models.Model):
    name = models.CharField(max_length=100, null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)

    def __str__(self):
        return self.name


class UserContacts(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_contact")
    user_contacted = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                       related_name="contacted_user",
                                       null=True, blank=True)
    name = models.CharField(max_length=30, null=True, blank=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    date_contacted = models.DateField()
    latitude = models.CharField(max_length=60, null=True, blank=True)
    longitude = models.CharField(max_length=60, blank=True, null=True)
    is_infected = models.BooleanField(default=False)
    location = models.CharField(max_length=100, blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)
    is_tagged = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class UserContactTagging(models.Model):
    user_contact = models.ForeignKey(UserContacts, on_delete=models.CASCADE, related_name="user_contact_tagging")
    from_time = models.TimeField()
    to_time = models.TimeField()
    latitude = models.CharField(max_length=60, null=True, blank=True)
    longitude = models.CharField(max_length=60, blank=True, null=True)
    is_infected = models.BooleanField(default=False)
    date_created = models.DateField(auto_now_add=True)
    place_tag = models.CharField(max_length=100, blank=True, null=True)
    updated_at = models.DateField(auto_now=True)

    def __str__(self):
        return self.to_time
