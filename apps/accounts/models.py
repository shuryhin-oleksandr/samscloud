from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from django.dispatch import receiver
from django.conf import settings

from django_rest_passwordreset.signals import reset_password_token_created

from apps.accounts.api.utils import get_site_url, send_email_for_user

USER_TYPE = (
    ('Individual', 'Individual'),
    ('Responder', 'Responder'),
)


class CustomUserManager(BaseUserManager):

    def create_user(self, email, password=None, **extra_fields):
        """
        Creates and saves a User with the given email and password.
        """
        now = timezone.now()
        if not email:
            raise ValueError('The given email must be set')
        email = CustomUserManager.normalize_email(email)
        user = self.model(email=email,
                          is_staff=False, is_active=True, is_superuser=False,
                          last_login=now, date_joined=now, **extra_fields)

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        """
        creates a superuser with the given email and password
        :param email: accepts user email
        :param password: accepts user password
        :param extra_fields:
        :return: created user
        """
        u = self.create_user(email, password, **extra_fields)
        u.is_staff = True
        u.is_active = True
        u.is_superuser = True
        u.save(using=self._db)
        return u


class User(AbstractBaseUser, PermissionsMixin):
    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_('Designates whether the user can log into this admin site.'),
    )
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_(
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'
        ),
    )
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)
    email = models.EmailField(_('email address'), unique=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    user_type = models.CharField(choices=USER_TYPE, blank=True, null=True, max_length=15)
    profile_logo = models.ImageField(verbose_name="User Profile Logo", blank=True, upload_to='static/media/')
    address = models.TextField(blank=True, null=True)
    state = models.CharField(max_length=30, blank=True, null=True)
    city = models.CharField(max_length=30, blank=True, null=True)
    country = models.CharField(max_length=50, blank=True, null=True)
    zip = models.CharField(max_length=10, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    photo_location = models.TextField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    is_phone_number_verified = models.BooleanField(default=False)
    device_id = models.CharField(max_length=40, blank=True, null=True)
    lat = models.FloatField(verbose_name="Latitude", max_length=10, blank=True, null=True)
    long = models.FloatField(verbose_name="Longitude", max_length=10, blank=True, null=True)
    altitude = models.FloatField(verbose_name="Altitude", max_length=10, blank=True, null=True)
    speed = models.FloatField(verbose_name="Speed", max_length=10, blank=True, null=True)
    location_time = models.DateTimeField(verbose_name="Location Time", blank=True, null=True)
    pending_status = models.BooleanField(default=False)
    battery_power = models.CharField(max_length=10, null=True, blank=True)
    subscription_count = models.CharField(max_length=10, null=True, blank=True)
    is_subscribed = models.BooleanField(default=False)
    objects = CustomUserManager()

    USERNAME_FIELD = 'email'

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def profile_logo_tag(self):
        return u'<img src="/%s" />' % self.profile_logo

    profile_logo_tag.short_description = 'Image'
    profile_logo_tag.allow_tags = True


class MobileOtp(models.Model):
    otp = models.CharField(max_length=5, blank=True, null=True)
    user = models.ForeignKey("User", on_delete=models.CASCADE)
    message_id = models.CharField(max_length=50, blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.first_name + "-" + self.otp

@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, *args, **kwargs):
    """
    Handles password reset tokens
    When a token is created, an e-mail needs to be sent to the user
    :param sender: View Class that sent the signal
    :param instance: View Instance that sent the signal
    :param reset_password_token: Token Model Object
    :param args:
    :param kwargs:
    :return:
    """
    # send an e-mail to the user
    context = {
        'current_user': reset_password_token.user,
        'username': reset_password_token.user.first_name,
        'email': reset_password_token.user.email,
        'reset_password_url': "{0}://{1}/{2}?token={3}".format(
                                                         getattr(settings, 'ABSOLUTEURI_PROTOCOL', 'http'),
                                                         settings.FRONTEND_DOMAIN,
                                                         settings.FRONTEND_FORGOT_PASSWORD_URL,
                                                         reset_password_token.key),
    }

    template_name = 'email/user_reset_password'
    subject = 'Recover Password'
    recipient = reset_password_token.user.email
    send_email_for_user(context, template_name, subject, recipient)


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class ForgotPasswordOTP(models.Model):
    otp = models.CharField(max_length=5, blank=True, null=True)
    user = models.ForeignKey("User", on_delete=models.CASCADE)
    message_id = models.CharField(max_length=50, blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.first_name + "-" + self.otp