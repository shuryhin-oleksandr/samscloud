from django.conf import settings
from django.urls import reverse
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.models import Site
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from twilio.rest import Client
from rest_framework_simplejwt.tokens import RefreshToken
from celery.decorators import task
from fcm_django.models import FCMDevice


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


def send_account_activation_email(request, user):
    """
    Function to send User activation mail
    :param request:
    :param user:
    :return:
    """
    template_name = 'email/account_activation'
    subject = 'Account Activation - SamsCloud'
    recipients = user.email

    activate_url = "{0}://{1}accounts/activate/{2}/{3}".format(request.scheme,
                                                               get_site_url(),
                                                               urlsafe_base64_encode(force_bytes(user.pk)),
                                                               default_token_generator.make_token(user)
                                                               )

    context = {
        'first_name': user.first_name,
        'activate_url': activate_url
    }
    send_email_for_user.delay(context, template_name, subject, recipients)


def send_organization_activation_email(request, user, organization):
    """
    function to send organization activation mail
    :param request:
    :param user:
    :param organization: Organization Object
    :return:
    """
    template_name = 'email/account_activation'
    subject = 'Account Activation - SamsCloud'
    recipients = user.email
    activate_url = "{0}://{1}/accounts/activate?uid={2}&token={3}&code={4}".format(request.scheme,
                                                                                   settings.FRONTEND_DOMAIN,
                                                                                   urlsafe_base64_encode(
                                                                                       force_bytes(user.pk)),
                                                                                   default_token_generator.make_token(
                                                                                       user),
                                                                                   organization.pro_code
                                                                                   )

    context = {
        'first_name': user.first_name,
        'activate_url': activate_url
    }
    send_email_for_user.delay(context, template_name, subject, recipients)


def send_organization_welcome_mail(request, user, organization):
    """
    Welcome mail for already existing users
    :param request:
    :param user:
    :param organization:
    :return:
    """
    template_name = 'email/account_activation_confirm'
    subject = 'Account Activated - SamsCloud'
    recipients = user.email
    context = {
        'first_name': user.first_name,
        'current_user': request.user.first_name,
        'organization': organization.organization_name,
    }
    send_email_for_user.delay(context, template_name, subject, recipients)


def send_emergency_contact_mail(request, uuid, name, email, contact_type):
    """
    Welcome mail for emergency contacts.
    :param request:
    :param uuid:
    :param name:
    :param email:
    :return:
    """
    template_name = 'email/emergency_contact'
    subject = '%s Conatct Added - SamsCloud' % (contact_type)
    recipients = email

    activate_url = "{0}://{1}/emergency-contact/activate?uid={2}".format(request.scheme,
                                                                         settings.FRONTEND_DOMAIN,
                                                                         uuid
                                                                         )

    context = {
        'first_name': request.user.first_name,
        'name': name,
        'activate_url': activate_url,
        'contact_type': contact_type
    }
    send_email_for_user.delay(context, template_name, subject, recipients)


def send_contact_mail(request, uuid, name, email, contact_type):
    """
    Welcome mail for family contacts.
    :param request:
    :param uuid:
    :param name:
    :param email:
    :return:
    """
    template_name = 'email/family_contact'
    subject = 'Samscloud incident from  %s ' % (request.user.first_nam)
    recipients = email

    activate_url = "{0}://{1}/emergency-contact/activate?uid={2}".format(request.scheme,
                                                                         settings.FRONTEND_DOMAIN,
                                                                         uuid
                                                                         )

    context = {
        'first_name': request.user.first_name,
        'name': name,
        'activate_url': activate_url,
        'contact_type': contact_type
    }
    send_email_for_user.delay(context, template_name, subject, recipients)


def send_organization_email_activation(request, organization):
    """
    Function for organization activation mail
    :param request:
    :param organization:
    :return:
    """
    template_name = 'email/organization_email_activation'
    subject = 'Activate Organization Mail - SamsCloud'
    recipients = organization.organization_email
    activate_url = "{0}://{1}/accounts/activate?uid={2}".format(request.scheme,
                                                                settings.FRONTEND_DOMAIN,
                                                                organization.id
                                                                )
    context = {
        'activate_url': activate_url,
        'name': request.user.first_name
    }
    send_email_for_user.delay(context, template_name, subject, recipients)


def send_mobile_forgot_email(request, user, password):
    """
    Function for forgot password
    :param request:
    :param user:
    :param password:
    :return:
    """
    template_name = 'email/mobile_forgot_password'
    subject = 'Forgot Password - SamsCloud'
    recipients = user.email
    context = {
        'password': password
    }
    send_email_for_user.delay(context, template_name, subject, recipients)


def send_password_reset_confirm_email(request, user):
    """
    Function for password reset
    :param request:
    :param user:
    :return:
    """
    template_name = 'email/password_reset_confirm'
    subject = 'Password Reset Confirm - SamsCloud'
    recipients = user.email

    context = {
        'name': user.first_name,
        'email': user.email
    }
    send_email_for_user.delay(context, template_name, subject, recipients)


def send_incident_link_to_emergecy_contacts(email, user_name, incident_user, url):
    """
    Function to send incident link to emergency contacts
    :param request:
    :param user:
    :param url:
    :return:
    """
    template_name = 'email/incident_link_to_emergency_contacts'
    subject = 'Incident Reporting - SamsCloud'
    recipients = email
    context = {
        'incident_url': url,
        'user_name': user_name,
        'incident_user': incident_user.first_name
    }
    send_email_for_user.delay(context, template_name, subject, recipients)


def send_incident_link_to_organization_contacts(email, user_name, incident_user, url):
    """
    Function to send incident link to emergency contacts
    :param request:
    :param user:
    :param url:
    :return:
    """
    template_name = 'email/incident_link_to_organization_contacts'
    subject = 'Incident Reporting - SamsCloud'
    recipients = email
    context = {
        'incident_url': url,
        'user_name': user_name,
        'incident_user': incident_user.first_name
    }
    send_email_for_user.delay(context, template_name, subject, recipients)


def send_incident_end_report(email, user_name, incident_user, reason):
    """
    Function to send incident end report to responders
    :param request:
    :param user:
    :param reason:
    :param url:
    :return:
    """
    template_name = 'email/incident_end_reporting'
    subject = 'Incident End Reporting - SamsCloud'
    recipients = email
    context = {
        'user_name': user_name,
        'incident_user': incident_user.first_name,
        'reason': reason
    }
    send_email_for_user.delay(context, template_name, subject, recipients)

def send_emergency_contact_status(email, user_name, contact_user, status):
    """
    Function to send incident end report to responders
    :param request:
    :param user:
    :param reason:
    :param url:
    :return:
    """
    template_name = 'email/emergency_contact_status'
    subject = 'Emergency Contact Status - SamsCloud'
    recipients = email
    context = {
        'user_name': user_name,
        'incident_user': contact_user,
        'reason': status
    }
    send_email_for_user.delay(context, template_name, subject, recipients)

@task(name="send_email_for_user")
def send_email_for_user(context, template_name, subject, recipient):
    """
    SMTP mail sending function view
    :param context:
    :param template_name:
    :param subject:
    :param recipient:
    :return:
    """
    email_html_message = render_to_string('%s.html' % template_name, context)
    email_plaintext_message = render_to_string('%s.txt' % template_name, context)
    from_email = settings.DEFAULT_FROM_EMAIL
    msg = EmailMultiAlternatives(subject, email_plaintext_message, from_email, [recipient])
    msg.attach_alternative(email_html_message, "text/html")
    msg.send()


def get_site_url():
    current_site = Site.objects.get_current()
    return current_site.domain


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


@task(name="send_push_notification")
def send_push_notification(fcm_obj_id, title, message, data):
    fcm_obj = FCMDevice.objects.get(id=fcm_obj_id)
    extra = {
        "contentAvailable": True,
    }
    response = fcm_obj.send_message(title=title, body=message, data=data, extra_kwargs=extra)
    if response['success'] == 1:
        print("Notification has sent to the user")
    else:
        print("Failed")
