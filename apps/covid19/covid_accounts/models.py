from decimal import Decimal

from django.contrib.auth.base_user import BaseUserManager, AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.core.validators import MinValueValidator
from django.contrib.auth import get_user_model
from django.db import models

from django.utils import timezone

from apps.covid19.contacts.models import Disease, Symptoms
from apps.covid19.vaccines.models import UserVaccine
User = get_user_model()


class Status(models.Model):
    status = models.CharField(max_length=100)
    date_created = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)

    class Meta:
        verbose_name_plural = "Statuses"

    def __str__(self):
        return self.status


class UserTesting(models.Model):
    TEST_TYPE = (
        ('Negative', 'Negative'),
        ('Positive', 'Positive'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_testing", blank=True, null=True)
    name = models.CharField(max_length=100, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    tested_date = models.DateField()
    test_result = models.CharField(max_length=20, choices=TEST_TYPE, default='Negative')
    file_upload = models.FileField(verbose_name="testing file", blank=True, upload_to='static/media/')
    is_reminded = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "User Testings"

    def __str__(self):
        return str(self.user)


class UserReport(models.Model):
    TEST_TYPE = (
        ('Negative', 'Negative'),
        ('Positive', 'Positive'),
    )
    CUR_SYM = (
        ('Actively Experiencing Symptoms', 'Actively Experiencing Symptoms'),
        ('Actively Not Experiencing Symptoms', 'Actively Not Experiencing Symptoms'),
    )
    VACCINE_MANUFACTURER_TYPE = (
        ('Moderna', 'Moderna'),
        ('Pfizer', 'Pfizer'),
        ('Johnson and Johnson', 'Johnson and Johnson'),
        ('Other', 'Other'),
    )
    VACCINE_DOSAGE = {
        ('1 of 1', '1 of 1'),
        ('1 of 2', '1 of 2'),
        ('2 of 2', '2 of 2'),
    }
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_report", blank=True, null=True)
    disease = models.ForeignKey(Disease, on_delete=models.CASCADE, related_name="user_disease")
    symptoms = models.ManyToManyField(Symptoms, related_name="user_symptoms", blank=True)
    tested_date = models.DateField(blank=True, null=True)
    data_started = models.DateField(blank=True, null=True)
    is_tested = models.BooleanField(default=False)
    test_result = models.CharField(max_length=20, choices=TEST_TYPE, default='Negative')
    current_status = models.CharField(max_length=50, choices=CUR_SYM, default='Actively Not Experiencing Symptoms',
                                      blank=True, null=True)
    status = models.ForeignKey(Status, on_delete=models.CASCADE, related_name="report_status", blank=True, null=True)
    port = models.CharField(max_length=50, blank=True, null=True)
    testing = models.ForeignKey(UserTesting, on_delete=models.SET_NULL, related_name="user_testing", blank=True,
                                null=True)
    is_vaccinated = models.BooleanField(default=False)
    vaccine = models.ForeignKey(UserVaccine, on_delete=models.SET_NULL, related_name="user_vaccine", blank=True,
                                null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)

    class Meta:
        verbose_name_plural = "User Reports"

    def __str__(self):
        return str(self.id)


class Lastupdated(models.Model):
    updated_time = models.DateTimeField()
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Last Updated"

    def __str__(self):
        return self.updated_time
