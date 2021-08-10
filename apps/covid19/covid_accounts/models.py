from django.contrib.auth import get_user_model
from django.db import models

from apps.accounts.models import AbstractTimeStampedModel
from apps.covid19.contacts.models import Disease, Symptoms
from apps.covid19.vaccines.models import UserVaccine
from utils.constants import SCREENING_OK_STATUS, SCREENING_NEED_TEST_STATUS
from utils.table_names import (SCREENING_TABLE_NAME, SCREENING_QUESTION_TABLE_NAME,
                               SCREENING_ANSWER_OPTION_TABLE_NAME, SCREENING_USER_TABLE_NAME,
                               SCREENING_ANSWER_TABLE_NAME)

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


class Screening(AbstractTimeStampedModel):
    title = models.CharField(max_length=100)
    time_at = models.TimeField()

    class Meta:
        db_table = SCREENING_TABLE_NAME
        ordering = ('id',)

    def __str__(self):
        return f'Screening at {self.time_at}'


class ScreeningQuestion(AbstractTimeStampedModel):
    screening = models.ForeignKey(Screening, on_delete=models.CASCADE, related_name='questions')
    title = models.CharField(max_length=200)
    multiple = models.BooleanField(default=True)

    class Meta:
        db_table = SCREENING_QUESTION_TABLE_NAME
        ordering = ('id',)


class ScreeningQuestionOption(AbstractTimeStampedModel):
    question = models.ForeignKey(
        ScreeningQuestion,
        on_delete=models.CASCADE,
        related_name='options'
    )
    text = models.CharField(max_length=200)
    is_symptom = models.BooleanField(default=False)

    class Meta:
        db_table = SCREENING_ANSWER_OPTION_TABLE_NAME
        ordering = ('id',)


class ScreeningUser(AbstractTimeStampedModel):
    user = models.ForeignKey(
        User,
        related_name='screening_users',
        on_delete=models.CASCADE,
    )
    screening = models.ForeignKey(
        Screening,
        related_name='screening_users',
        on_delete=models.CASCADE,
    )
    answered_at = models.DateTimeField()

    @property
    def status(self):
        if self.screening_answers.filter(screening_answer_option__is_symptom=True).exists():
            return SCREENING_NEED_TEST_STATUS
        else:
            return SCREENING_OK_STATUS

    class Meta:
        db_table = SCREENING_USER_TABLE_NAME
        ordering = ('id',)


class ScreeningAnswer(AbstractTimeStampedModel):
    screening_answer_option = models.ForeignKey(
        ScreeningQuestionOption,
        on_delete=models.CASCADE,
        related_name='screening_answers'
    )
    screening_user = models.ForeignKey(
        ScreeningUser,
        on_delete=models.CASCADE,
        related_name='screening_answers'
    )
    filled = models.BooleanField(default=False)

    class Meta:
        db_table = SCREENING_ANSWER_TABLE_NAME
        ordering = ('id',)
