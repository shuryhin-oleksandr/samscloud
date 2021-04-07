from django.conf import settings
from django.db import models


class UserLocations(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_locations")
    location = models.CharField(max_length=255, blank=True, null=True)
    Country_Region = models.CharField(max_length=255, blank=True, null=True)
    City = models.CharField(max_length=255, blank=True, null=True)
    Province_State = models.CharField(max_length=255, blank=True, null=True)
    location_date = models.DateField()
    latitude = models.CharField(max_length=100, null=True, blank=True)
    longitude = models.CharField(max_length=100, blank=True, null=True)
    from_time = models.TimeField(blank=True, null=True)
    to_time = models.TimeField(blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)
    is_infected = models.BooleanField(default=False)
    place_tag = models.CharField(max_length=255, blank=True, null=True)
    is_hidden = models.BooleanField(default=False)

    def __str__(self):
        return self.user.first_name


class UserLocationTagging(models.Model):
    user_location = models.ForeignKey(UserLocations, on_delete=models.CASCADE, related_name="user_location_tagging")
    from_time = models.TimeField()
    to_time = models.TimeField()
    is_infected = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)


class GlobalLocations(models.Model):
    Province_State = models.CharField(max_length=255, blank=True, null=True)
    City = models.CharField(max_length=255, blank=True, null=True)
    County = models.CharField(max_length=255, blank=True, null=True)
    Country_Region = models.CharField(max_length=255, blank=True, null=True)
    Last_Update = models.DateTimeField(blank=True, null=True)
    Lat = models.CharField(max_length=100, blank=True, null=True)
    Long = models.CharField(max_length=100, blank=True, null=True)
    Confirmed = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    Deaths = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    Recovered = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    Active = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return self.Country_Region


class AssistanceLocations(models.Model):
    Activity = (
        ('Food Aid', 'Food Aid'),
        ('Supplies', 'Supplies'),
        ('Financial Help', 'Financial Help'),
        ('Test Center', 'Test Center'),
        ('Vaccine', 'Vaccine'),
    )
    Type = (
        ('Giveaway', 'Giveaway'),
        ('Assistance', 'Assistance'),
    )
    Display = (
        ('2 weeks', '2 weeks'),
        ('3 weeks', '3 weeks'),
        ('4 weeks', '4 weeks'),
        ('5 weeks', '5 weeks'),
        ('6 weeks', '6 weeks'),
        ('7 weeks', '7 weeks'),
        ('8 weeks', '8 weeks'),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_assistance")
    location = models.CharField(max_length=255, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    Country_Region = models.CharField(max_length=255, blank=True, null=True)
    Province_State = models.CharField(max_length=255, blank=True, null=True)
    activity = models.CharField(max_length=100, choices=Activity, default='Food Aid', blank=True, null=True)
    type = models.CharField(max_length=100, choices=Type, default='Giveaway', blank=True, null=True)
    dispaly_location = models.CharField(max_length=100, choices=Display, default='2 weeks', blank=True, null=True)
    phone_number = models.CharField(max_length=20)
    to_date = models.DateField()
    from_date = models.DateField()
    latitude = models.CharField(max_length=100, null=True, blank=True)
    longitude = models.CharField(max_length=100, blank=True, null=True)
    from_time = models.TimeField(blank=True, null=True)
    to_time = models.TimeField(blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)
    permanent = models.BooleanField(default=False)

    def __str__(self):
        return self.location
