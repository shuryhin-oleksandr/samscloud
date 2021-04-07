from django.conf import settings
from django.db import models


class Flight(models.Model):
    name = models.CharField(max_length=100)
    date_created = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)

    def __str__(self):
        return self.name


class FlightDetails(models.Model):
    flight = models.ForeignKey(Flight, on_delete=models.CASCADE, related_name="flight_group")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_flight")
    flight_no = models.CharField(max_length=50, blank=True, null=True)
    date_journey = models.DateField()
    is_infected = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)

    def __str__(self):
        return self.flight_no


class Questions(models.Model):
    QUEST_TYPE = (
        ('GENERAL', 'GENERAL'),
        ('ADVANCED', 'ADVANCED'),
    )
    question = models.TextField(blank=True)
    type = models.CharField(max_length=20, choices=QUEST_TYPE, default='GENERAL')
    date_created = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)

    def __str__(self):
        return self.question


class UserAnswers(models.Model):
    question = models.ForeignKey(Questions, on_delete=models.CASCADE, related_name="answer_question")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_question")
    is_correct = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)

    def __str__(self):
        return self.user.email
