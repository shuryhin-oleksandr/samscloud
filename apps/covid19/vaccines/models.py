from django.conf import settings
from django.db import models

from apps.covid19.contacts.models import Disease


class Dose(models.Model):
    name = models.CharField(max_length=100)
    parent = models.ForeignKey('self', blank=True, null=True, on_delete=models.CASCADE, related_name='children')
    date_created = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)

    def __str__(self):
        return self.name


class Manufacturer(models.Model):
    name = models.CharField(max_length=100)
    disease = models.ForeignKey(Disease, on_delete=models.CASCADE, related_name="manufacturer_disease")
    requirement_dose = models.ForeignKey(Dose, on_delete=models.CASCADE, related_name="manufacturer_dose")
    frequency = models.IntegerField(blank=True, null=True)
    validity_period = models.IntegerField(blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)

    def __str__(self):
        return self.name


class UserVaccine(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_vaccine",
                             blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    vaccinated_date = models.DateField()
    manufacturer = models.ForeignKey(Manufacturer, on_delete=models.CASCADE, related_name="vaccine_manufacturer")
    lot = models.CharField(max_length=100, blank=True, null=True)
    dosage = models.ForeignKey(Dose, on_delete=models.CASCADE, related_name="vaccine_dose")
    file_upload = models.FileField(verbose_name="vaccination file", blank=True, upload_to='static/media/')
    is_reminded = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.first_name
