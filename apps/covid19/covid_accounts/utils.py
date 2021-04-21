import csv
import datetime
import json
import os

import pytz
import requests
from celery.schedules import crontab
from celery.task import periodic_task
from django.conf import settings
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from celery.decorators import task
from django.utils.timezone import make_aware
from twilio.rest import Client
from rest_framework_simplejwt.tokens import RefreshToken
import dateutil.parser
import subprocess

from apps.accounts.api.utils import send_email_for_user
from apps.covid19.flight.models import Flight
from apps.covid19.location.models import GlobalLocations, AssistanceLocations
from apps.covid19.covid_accounts.models import UserReport
from apps.covid19.vaccines.models import UserVaccine


def get_tokens_for_user(user):
    """
    Function to generate token for User
    :param user: user
    :return:
    """
    refresh = RefreshToken.for_user(user)

    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


@periodic_task(run_every=crontab(minute=0, hour=0))
def send_user_next_vaccination_notification():
    try:
        date = datetime.date.today()
        first_date = date + datetime.timedelta(days=14)
        second_date = date + datetime.timedelta(days=7)

        vaccinated_reports = UserReport.objects.filter(is_vaccinated=True)
        for report in vaccinated_reports:
            latest_vaccine = UserVaccine.objects.filter(user=report.user).order_by('vaccinated_date').last()
            if latest_vaccine is None:
                continue
            if latest_vaccine.dosage.parent:
                frequency = latest_vaccine.manufacturer.frequency
                next_dosage_day = latest_vaccine.vaccinated_date + datetime.timedelta(days=frequency)
                if first_date == next_dosage_day or second_date == next_dosage_day:
                    if latest_vaccine.user.phone_number:
                        message = f"Dear, {latest_vaccine.user.first_name}, " \
                                  f"you have to get the next dose of {latest_vaccine.manufacturer} " \
                                  f"vaccine on {next_dosage_day.strftime('%Y-%m-%d')}!"
                        send_twilio_sms.delay(message, latest_vaccine.user.phone_number)
                    # if latest_vaccine.user.email:
                    #     send_next_vaccine_dose_email_notification(latest_vaccine.user.email,
                    #                                               latest_vaccine.user.first_name,
                    #                                               latest_vaccine.manufacturer,
                    #                                               next_dosage_day.strftime(
                    #                                                   "%Y-%m-%d"))
            else:
                validity_period = latest_vaccine.manufacturer.validity_period
                if validity_period is None:
                    validity_period = 365
                next_vaccine_day = latest_vaccine.vaccinated_date + datetime.timedelta(days=validity_period)
                if first_date == next_vaccine_day or second_date == next_vaccine_day:
                    if latest_vaccine.user.phone_number:
                        message = f"Dear, {latest_vaccine.user.first_name}, " \
                                  f"you have to get the new vaccine, because validity period " \
                                  f"of latest is expired on  {next_vaccine_day.strftime('%Y-%m-%d')}!"
                        send_twilio_sms.delay(message, latest_vaccine.user.phone_number)
                    # if latest_vaccine.user.email:
                    #     send_next_vaccine_dose_email_notification(latest_vaccine.user.email,
                    #                                               latest_vaccine.user.first_name,
                    #                                               latest_vaccine.manufacturer,
                    #                                               next_vaccine_day.strftime(
                    #                                                   "%Y-%m-%d"))
    except Exception as e:
        print("Unable to send message because of", e)


def send_next_vaccine_dose_email_notification(email, user_name, manufacturer, date):
    """
    Function to send notification for next dosage to user
    :param email:
    :param user_name:
    :param manufacturer:
    :param date:
    :return:
    """
    template_name = 'email/vaccine_next_dosage_notification'
    subject = 'Next vaccine dose notification - COVID19 SamsCloud'
    recipients = email
    context = {
        'user_name': user_name,
        'manufacturer_name': manufacturer.name,
        'date': date
    }
    send_email_for_user.delay(context, template_name, subject, recipients)


@task(name="send_twilio_sms")
def send_twilio_sms(message, to):
    """
    Celery task to send SMS using Twilio client
    :param message: message body
    :param to: Receiver phone number
    :return:
    """
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    try:
        message = client.messages.create(
            body=message,
            to=to,
            from_=settings.TWILIO_FROM_NUMBER,
        )
        if message:
            print("Message send successfully")
    except Exception as e:
        print("Unable to send message because of", e)


@periodic_task(run_every=crontab(minute='*/2'))
def get_global_covid_data():
    date = datetime.date.today()
    previous = date - datetime.timedelta(days=1)

    try:
        URL = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_daily_reports/%s-%s-%s.csv" % (
            previous.strftime('%m'), previous.strftime('%d'), previous.strftime('%Y'))
        r = requests.get(url=URL)
        data = r.text
        file = open("response.csv", "w")
        file.write(data)
        file.close()
        with open('response.csv', "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        with open('response.json', 'w') as f:
            json.dump(rows, f)
        with open('response.json') as f:
            data = json.load(f)
        GlobalLocations.objects.all().delete()
        for k in data:
            datestime = datetime.datetime.strptime(k.get('Last_Update', None), "%Y-%m-%d %H:%M:%S")
            globals = GlobalLocations(Province_State=k.get('Province_State', None), County=k.get('FIPS', None),
                                      City=k.get('Admin2', None), Country_Region=k.get('Country_Region', None),
                                      Last_Update
                                      =make_aware(datestime), Lat=k.get('Lat', None), Long=k.get('Long_', None),
                                      Confirmed=k.get('Confirmed', None) or 0.00,
                                      Deaths=k.get('Deaths', None) or 0.00, Recovered=k.get('Recovered', None) or 0.00,
                                      Active=k.get('Active', None) or 0.00)
            globals.save()
    except Exception as e:
        print("Unable to fetch data from link", e)


def load_flight_carrier():
    with open('flightcarrier.JSON') as f:
        data = json.load(f)
    for k in data:
        flight = Flight(name=k.get('name', None))
        flight.save()


@periodic_task(run_every=crontab(minute=0, hour='*/8'))
def load_labs_data():
    os.chdir("/home/ubuntu/covid-19-backend/geo-loc-fetch/")
    cmd = "npm start /home/ubuntu/covid-19-backend/labs/"

    # returns output as byte string
    subprocess.call(cmd, shell=True)


@periodic_task(run_every=crontab(minute=0, hour='0'))
def delete_outdated_assistance_data():
    try:
        date = datetime.date.today()
        outdated = AssistanceLocations.objects.filter(to_date__lt=date)
        for date in outdated:
            date.delete()
    except Exception as e:
        print("Unable to delete outdated data", e)
