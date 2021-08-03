import datetime
import re
from random import randint

import requests
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import CharField, EmailField
from rest_framework.serializers import ModelSerializer, Serializer

from apps.accounts.models import User, MobileOtp
from apps.covid19.contacts.api.serializers import SymptomsSerializer
from apps.covid19.contacts.models import Symptoms, Disease, UserContacts
from apps.covid19.covid_accounts.models import (UserReport, Status, Lastupdated, UserTesting,
                                                ScreeningUser, ScreeningAnswer, Screening,
                                                ScreeningQuestion, ScreeningQuestionOption)
from apps.covid19.covid_accounts.utils import send_twilio_sms, get_tokens_for_user
from apps.covid19.flight.models import FlightDetails
from apps.covid19.location.models import UserLocations
from apps.covid19.vaccines.api.serializers import UserVaccineSerializer
from apps.covid19.vaccines.models import UserVaccine


class UserCreateSerializer(ModelSerializer):
    """
    User Register serializer
    """
    confirm_password = CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'id',
            'first_name',
            'last_name',
            'email',
            'address',
            'state',
            'city',
            'zip',
            'date_of_birth',
            'user_type',
            'racial_group',
            'gender',
            'password',
            'country',
            'confirm_password',
            'phone_number',
            'risk_level',
            'contact_exposure',
            'location_exposure',
            'flight_exposure',
            'last_login',
            'last_updated'
        ]
        read_only_fields = (
            "id", "risk_level", "contact_exposure", "location_exposure", "flight_exposure", "last_login",
            "last_updated",)

    def validate_email(self, value):
        email = value.lower().strip()

        user_qs = User.objects.filter(email=email)

        if user_qs.exists():
            raise ValidationError("This user has already registered.")

        return value

    def validate_phone_number(self, value):
        phone_number = value
        user_qs = User.objects.filter(phone_number=phone_number)
        if user_qs.exists():
            raise ValidationError("This phone has already registered.")
        return value

    def validate_password(self, value):
        data = self.get_initial()
        password1 = value
        password2 = data.get('confirm_password')
        if password1 != password2:
            raise ValidationError('Passwords Must Match')
        if not re.match(r"^(?=.*[\d])(?=.*[A-Z])(?=.*[a-z])(?=.*[~!@#$%^&*()_+\.])[\w\d~!@#$%^&*()_+\.]{6,}$",
                        password1):
            raise ValidationError(
                'Your password has to be at least 6 characters long.'
                ' Must contain at least one lower case letter, '
                'one upper case letter, one digit. at least one special character'
                ' ~!@#$%^&*()_+.')
        return value

    def create(self, validated_data):
        first_name = validated_data.get('first_name', None)
        last_name = validated_data.get('last_name', None)
        email = validated_data.get('email', None)
        address = validated_data.get('address', None)
        state = validated_data.get('state', None)
        city = validated_data.get('city', None)
        country = validated_data.get('country', None)
        date_of_birth = validated_data.get('date_of_birth', None)
        user_type = validated_data.get('user_type', None)
        racial_group = validated_data.get('racial_group', None)
        gender = validated_data.get('gender', None)
        zip = validated_data.get('zip', None)
        phone_number = validated_data.get('phone_number', None)
        user_obj = User(
            first_name=first_name,
            last_name=last_name,
            email=email.lower().strip(),
            address=address,
            state=state,
            city=city,
            country=country,
            date_of_birth=date_of_birth,
            user_type=user_type,
            racial_group=racial_group,
            gender=gender,
            zip=zip,
            phone_number=phone_number,
            is_active=False,
        )
        user_obj.set_password(validated_data['password'])
        user_obj.last_updated = timezone.now()
        user_obj.save()
        last_updated = Lastupdated(updated_time=timezone.now())
        last_updated.save()
        try:
            user = User.objects.get(email=email.lower().strip())
            otp = randint(1000, 9999)
            mobile_otp = MobileOtp(user=user, otp=otp)
            mobile_otp.save()
            message = "Your verification code is %s" % otp
            send_twilio_sms.delay(message, phone_number)
            last_updated = Lastupdated(updated_time=timezone.now())
            last_updated.save()
        except:
            pass
        try:
            samscloud_url = "https://api.samscloud.io/api/users/register/"
            params = {
                "first_name": first_name,
                "last_name": last_name,
                "email": email.lower().strip(),
                "password": validated_data['password'],
                "confirm_password": validated_data['password']
            }
            r = requests.post(url=samscloud_url, data=params)
            data = r.status_code
            if data == 201:
                message = "Your created account in samscloud app"
        except:
            pass
        return validated_data


class MobileOTPSerializer(Serializer):
    """
    Serializer to verify SMS OTP
    """
    phone_number = CharField(label='Phone Number')
    otp = CharField(label='Enter OTP')

    def validate(self, data):
        otp = data.get("otp", None)
        if not otp:
            raise ValidationError('Please enter the OTP')
        if len(otp) != 4:
            raise ValidationError('The OTP Should be 4 digits')
        return data


class UserLoginSerializer(ModelSerializer):
    """
    User Login Serializer
    """
    token = CharField(allow_blank=True, read_only=True)
    refresh_token = CharField(allow_blank=True, read_only=True)
    email = EmailField(label='Email Address')

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'password',
            'token',
            'refresh_token'
        ]
        extra_kwargs = {"password": {"write_only": True},
                        }

    def get_verified_status(self, obj):
        user_obj = User.objects.get(id=obj.get('id'))
        if not (user_obj.is_active and user_obj.is_phone_number_verified):
            return False
        return True

    def validate(self, data):
        user_obj = None
        email = data.get("email", None)
        password = data["password"]
        if not email or not password:
            raise ValidationError("Email and password required")
        email = email.lower().strip()
        user = User.objects.filter(email=email).distinct()
        if user.exists() and user.count() == 1:
            user_obj = user.first()
        else:
            raise ValidationError('There is no user registered with %s' % email)
        if user_obj:
            if user_obj.is_phone_number_verified == False:
                raise ValidationError('You have not verified your account. Please verify it before login')
            if not user_obj.check_password(password):
                raise ValidationError('Incorrect credentials. Please try again')
        response_token = get_tokens_for_user(user_obj)

        data['token'] = response_token.get('access', None)
        data['refresh_token'] = response_token.get('refresh', None)
        data['id'] = user_obj.id
        user_obj.last_login = timezone.now()
        user_obj.save()
        return data


class MobileNumberSerializer(Serializer):
    """
    Serializer to send SMS OTP
    """
    mobile_number = CharField(label='Mobile Number')

    def validate(self, data):
        mobile_number = data.get("mobile_number", None)
        if not mobile_number:
            raise ValidationError('Mobile number can not be null')
        if not User.objects.filter(phone_number=mobile_number).exists():
            raise ValidationError('No user found for phone number')
        return data


class StatusSerializer(ModelSerializer):
    """
    status detail serializer
    """

    class Meta:
        model = Status
        fields = "__all__"
        read_only_fields = ("id",)


class UserTestingSerializer(ModelSerializer):
    """
    User Testing serializer
    """

    class Meta:
        model = UserTesting
        fields = "__all__"
        read_only_fields = ("id", "user")


class UserTestingUpdateSerializer(ModelSerializer):
    """
    user testing serializer
    """
    user = serializers.IntegerField()
    name = serializers.CharField(required=False, allow_blank=True, max_length=100)
    location = serializers.CharField(required=False, allow_blank=True, max_length=255)
    tested_date = serializers.DateField(format="%Y-%m-%d", required=False)
    test_result = serializers.CharField(required=False, allow_blank=True, max_length=100)
    file_upload = serializers.FileField(required=False)
    empty_file = serializers.BooleanField(required=False)

    class Meta:
        model = UserTesting
        fields = "__all__"
        read_only_fields = ("id", "user")

    def update(self, instance, validated_data):
        """
        Update and return an existing `Snippet` instance, given the validated data.
        """
        return_data = validated_data.copy()
        user = User.objects.filter(id=validated_data.get("user")).first()
        instance.user = user
        instance.name = validated_data.get("name")
        instance.location = validated_data.get("location")
        instance.tested_date = validated_data.get("tested_date")
        if validated_data.get('empty_file'):
            if instance.file_upload:
                instance.file_upload = None
                # if os.path.isfile(instance.file_upload.path):
                #     os.remove(instance.file_upload.path)
                #     instance.file_upload = None
        if validated_data.get('file_upload'):
            instance.file_upload = validated_data.get('file_upload')
        instance.save()
        report = UserReport.objects.filter(user=user).last()
        last_testing = UserTesting.objects.filter(user=user).order_by('-tested_date').last()
        if report is not None and instance.tested_date > last_testing.tested_date:
            report.testing = instance
            report.save()
        return return_data


class UserReportSerializer(ModelSerializer):
    """
    User Report Register serializer
    """
    symptoms = SymptomsSerializer(many=True)
    status = StatusSerializer(read_only=True)
    vaccine = UserVaccineSerializer(read_only=True)
    testing = UserTestingSerializer(read_only=True)

    def create(self, validated_data):
        symptoms = validated_data.pop("symptoms", {})
        user_report = UserReport.objects.create(**validated_data)
        new_symtops = [each_sym for each_sym in symptoms if not each_sym.isdigit()]
        new_symtopsdigits = [each_sym for each_sym in symptoms if each_sym.isdigit()]
        for i in new_symtops:
            p, created = Symptoms.objects.get_or_create(name=i)
            new_symtopsdigits.append(created.id)
        if new_symtopsdigits:
            user_report.symptoms.add(*new_symtopsdigits)

        return user_report

    # def update(self, instance, validated_data):
    #     sub_parties = validated_data.pop("sub_parties", [])
    #     instance.name = validated_data.get("name", instance.name)
    #     instance.code = validated_data.get("code", instance.code)
    #     instance.details = validated_data.get("details", instance.name)
    #
    #     instance.save()
    #
    #     for sub_party in sub_parties:
    #         SubParty.objects.create(project=instance, **sub_party)
    #     return instance

    class Meta:
        model = UserReport
        fields = "__all__"
        read_only_fields = ("id", "user", "current_status",)


class UserReportWriteSerializer(serializers.Serializer):
    disease = serializers.IntegerField()
    user_id = serializers.IntegerField()
    symptoms = serializers.ListField(
        child=serializers.CharField(allow_blank=True, max_length=100)
    )
    test_result = serializers.CharField(required=False, allow_blank=True, max_length=100)
    status = serializers.IntegerField(required=False)
    port = serializers.CharField(required=False, allow_blank=True, max_length=100)
    is_tested = serializers.BooleanField(default=False)
    tested_date = serializers.DateField(format="%Y-%m-%d", required=False)
    data_started = serializers.DateField(format="%Y-%m-%d", required=False)
    testing_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    is_vaccinated = serializers.BooleanField(default=False)
    vaccine_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    vaccinated_date = serializers.DateField(format="%Y-%m-%d", required=False)
    lot = serializers.CharField(required=False, allow_blank=True, max_length=100)
    dosage = serializers.IntegerField(required=False)
    manufacturer = serializers.IntegerField(required=False)
    is_reminded = serializers.BooleanField(default=False)

    def validate_testing_id(self, value):
        if not value:
            return 0
        try:
            return int(value)
        except ValueError:
            raise serializers.ValidationError('You must supply an integer')

    def validate_vaccine_id(self, value):
        if not value:
            return 0
        try:
            return int(value)
        except ValueError:
            raise serializers.ValidationError('You must supply an integer')

    def create(self, validated_data):
        return_data = validated_data.copy()
        symptoms = validated_data.pop("symptoms", {})
        disease = Disease.objects.filter(id=validated_data.get("disease")).first()
        user = User.objects.filter(id=validated_data.get("user_id")).first()
        status = Status.objects.filter(id=validated_data.get("status")).first()
        vaccine = None
        testing = None
        if validated_data.get("is_vaccinated"):
            vaccine = UserVaccine(vaccinated_date=validated_data.get("vaccinated_date"),
                                  lot=validated_data.get("lot"),
                                  dosage_id=validated_data.get("dosage"),
                                  manufacturer_id=validated_data.get("manufacturer"),
                                  is_reminded=validated_data.get("is_reminded"), user=user)
            vaccine.save()
        if validated_data.get("is_tested"):
            testing = UserTesting(tested_date=validated_data.get("tested_date"),
                                  test_result=validated_data.get("test_result"), user=user)
            testing.save()
        user_report = UserReport.objects.create(disease=disease, test_result=validated_data.get("test_result", ''),
                                                status=status,
                                                port=validated_data.get("port", ''),
                                                is_tested=validated_data.get("is_tested"),
                                                tested_date=validated_data.get("tested_date"),
                                                is_vaccinated=validated_data.get("is_vaccinated"),
                                                vaccine=vaccine,
                                                testing=testing,
                                                data_started=validated_data.get("data_started"), user=user)
        new_symtops = [each_sym for each_sym in symptoms if not each_sym.isdigit()]
        new_symtopsdigits = [each_sym for each_sym in symptoms if each_sym.isdigit()]
        for i in new_symtops:
            p, created = Symptoms.objects.get_or_create(name=i)
            if created == True:
                sym = Symptoms.objects.get(name=i)
                new_symtopsdigits.append(sym.id)
            else:
                sym = Symptoms.objects.get(name=i)
                new_symtopsdigits.append(sym.id)
        if new_symtopsdigits:
            user_report.symptoms.add(*new_symtopsdigits)
        user.last_updated = timezone.now()
        user.save()
        if validated_data.get("test_result") == "Positive":
            if validated_data.get("data_started"):
                UserLocations.objects.filter(user=user, location_date__gte=validated_data.get("data_started")).update(
                    is_infected=True)
                location = UserLocations.objects.filter(user=user,
                                                        location_date__gte=validated_data.get("data_started"))
                for loc in location:
                    delta = datetime.timedelta(hours=3)
                    start = (datetime.datetime.combine(datetime.date(9999, 1, 1), loc.from_time) - delta).time()
                    end = (datetime.datetime.combine(datetime.date(9999, 1, 1), loc.to_time) + delta).time()
                    UserLocations.objects.filter(location_date=loc.location_date, location=loc.location,
                                                 from_time__gte=start,
                                                 to_time__lte=end).update(
                        is_infected=True)
                    effect_location = UserLocations.objects.filter(location_date=loc.location_date,
                                                                   location=loc.location, from_time__gte=start,
                                                                   to_time__lte=end)
                    if effect_location:
                        for effect in effect_location:
                            try:
                                location_user = User.objects.get(id=effect.user.id)
                                location_user.location_exposure += 1
                                location_user.save()
                            except:
                                pass
                    user.risk_level = True
                    user.save()

                contacts = UserContacts.objects.filter(user=user, date_contacted__range=[
                    validated_data.get("data_started") - datetime.timedelta(days=15),
                    validated_data.get("data_started") + datetime.timedelta(days=15)])
                UserContacts.objects.filter(user=user, date_contacted__range=[
                    validated_data.get("data_started") - datetime.timedelta(days=15),
                    validated_data.get("data_started") + datetime.timedelta(days=15)]).update(
                    is_infected=True)
                for con in contacts:
                    try:
                        contact_user = User.objects.get(phone_number=con.phone_number)
                        if user != contact_user:
                            contact_user.contact_exposure += 1
                        contact_user.save()
                        user.risk_level = True
                        user.save()
                        # contact_location = UserLocations.objects.filter(location_date=con.date_contacted, location=con.location)
                        # contact_location.update(is_infected=True)

                    except:
                        user.risk_level = True
                        user.save()
                flight = FlightDetails.objects.filter(user=user, date_journey__range=[
                    validated_data.get("data_started") - datetime.timedelta(days=15),
                    validated_data.get("data_started") + datetime.timedelta(days=15)])
                FlightDetails.objects.filter(user=user, date_journey__range=[
                    validated_data.get("data_started") - datetime.timedelta(days=15),
                    validated_data.get("data_started") + datetime.timedelta(days=15)]).update(is_infected=True)
                for fli in flight:
                    effect_flight_user = FlightDetails.objects.filter(date_journey=fli.date_journey,
                                                                      flight=fli.flight, flight_no=fli.flight_no)
                    if effect_flight_user:
                        for effect in effect_flight_user:
                            try:
                                flight_user = User.objects.get(id=effect.user.id)
                                flight_user.flight_exposure += 1
                                flight_user.save()
                            except:
                                pass
                    user.risk_level = True
                    user.save()
        else:
            if validated_data.get("data_started"):
                UserLocations.objects.filter(user=user, location_date__gte=validated_data.get("data_started")).update(
                    is_infected=False)
                location = UserLocations.objects.filter(user=user,
                                                        location_date__gte=validated_data.get("data_started"))
                for loc in location:
                    delta = datetime.timedelta(hours=3)
                    start = (datetime.datetime.combine(datetime.date(9999, 1, 1), loc.from_time) - delta).time()
                    end = (datetime.datetime.combine(datetime.date(9999, 1, 1), loc.to_time) + delta).time()
                    effect_location = UserLocations.objects.filter(location_date=loc.location_date,
                                                                   location=loc.location, from_time__gte=start,
                                                                   to_time__lte=end)
                    if effect_location:
                        for effect in effect_location:
                            try:
                                location_user = User.objects.get(id=effect.user.id)
                                location_user.location_exposure -= 1
                                report = UserReport.objects.filter(user=location_user).first()
                                if user == location_user:
                                    location_user.is_infected = False
                                if report and report.test_result == "Negative":
                                    location_user.is_infected = False
                                if not report:
                                    location_user.is_infected = False
                                location_user.save()
                            except:
                                pass
                    user.risk_level = False
                    user.save()

                contacts = UserContacts.objects.filter(user=user, date_contacted__range=[
                    validated_data.get("data_started") - datetime.timedelta(days=15),
                    validated_data.get("data_started") + datetime.timedelta(days=15)])
                UserContacts.objects.filter(user=user, date_contacted__range=[
                    validated_data.get("data_started") - datetime.timedelta(days=15),
                    validated_data.get("data_started") + datetime.timedelta(days=15)]).update(is_infected=False)
                for con in contacts:
                    try:
                        contact_user = User.objects.get(phone_number=con.phone_number)
                        contact_user.contact_exposure -= 1
                        contact_user.save()
                        user.risk_level = False
                        user.save()
                    except:
                        user.risk_level = False
                        user.save()
                flight = FlightDetails.objects.filter(user=user, date_journey__range=[
                    validated_data.get("data_started") - datetime.timedelta(days=15),
                    validated_data.get("data_started") + datetime.timedelta(days=15)])
                FlightDetails.objects.filter(user=user, date_journey__range=[
                    validated_data.get("data_started") - datetime.timedelta(days=15),
                    validated_data.get("data_started") + datetime.timedelta(days=15)]).update(is_infected=False)
                for fli in flight:
                    effect_flight_user = FlightDetails.objects.filter(date_journey=fli.date_journey,
                                                                      flight=fli.flight, flight_no=fli.flight_no)
                    if effect_flight_user:
                        for effect in effect_flight_user:
                            try:
                                flight_user = User.objects.get(id=effect.user.id)
                                flight_user.flight_exposure -= 1
                                flight_user.save()
                            except:
                                pass
                    user.risk_level = False
                    user.save()
            else:
                UserLocations.objects.filter(user=user).update(
                    is_infected=False)
                UserContacts.objects.filter(user=user).update(is_infected=False)
                FlightDetails.objects.filter(user=user).update(is_infected=False)
        last_updated = Lastupdated(updated_time=timezone.now())
        last_updated.save()
        return return_data

    def to_representation(self, instance):
        user_id = instance.get('user_id')
        user = User.objects.filter(id=user_id).first()
        user_report = UserReport.objects.filter(user=user).last()
        data = super(UserReportWriteSerializer, self).to_representation(instance)
        data.update({'id': user_report.id})
        sym = [each_sym for each_sym in instance.get('symptoms') if not each_sym.isdigit()]
        sym_list = []

        for i in instance.get('symptoms'):
            if i.isdigit():
                symtoms_list = Symptoms.objects.get(id=i)
            else:
                symtoms_list = Symptoms.objects.get(name=i)

            if symtoms_list:
                sym_list.append({"id": symtoms_list.id, "name": symtoms_list.name})
        data['symptoms'] = sym_list

        return data

    def update(self, instance, validated_data):
        """
        Update and return an existing `Snippet` instance, given the validated data.
        """
        return_data = validated_data.copy()
        symptoms = validated_data.pop("symptoms", {})
        disease = Disease.objects.filter(id=validated_data.get("disease")).first()
        user = User.objects.filter(id=validated_data.get("user_id")).first()
        status = Status.objects.filter(id=validated_data.get("status")).first()
        instance.disease = disease
        instance.user = user
        instance.test_result = validated_data.get('test_result', 'Negative')
        if status:
            instance.status = status
        instance.port = validated_data.get('port')
        instance.is_tested = validated_data.get('is_tested', False)
        instance.tested_date = validated_data.get('tested_date')
        instance.is_vaccinated = validated_data.get('is_vaccinated', False)
        instance.data_started = validated_data.get('data_started')
        if validated_data.get("is_vaccinated"):
            if instance.vaccine_id:
                vaccine = UserVaccine.objects.get(id=instance.vaccine_id)
                vaccine.vaccinated_date = validated_data.get("vaccinated_date")
                vaccine.dosage_id = validated_data.get("dosage")
                vaccine.manufacturer_id = validated_data.get("manufacturer")
                vaccine.lot = validated_data.get("lot")
                vaccine.is_reminded = validated_data.get("is_reminded")
                vaccine.save()
            else:
                vaccine = UserVaccine(vaccinated_date=validated_data.get("vaccinated_date"),
                                      lot=validated_data.get("lot"),
                                      dosage_id=validated_data.get("dosage"),
                                      manufacturer_id=validated_data.get("manufacturer"),
                                      is_reminded=validated_data.get("is_reminded"), user=user)
                vaccine.save()
                instance.vaccine = vaccine
        if validated_data.get("is_tested"):
            if instance.testing_id:
                testing = UserTesting.objects.get(id=instance.testing_id)
                testing.tested_date = validated_data.get("tested_date")
                testing.test_result = validated_data.get("test_result")
                testing.save()
            else:
                testing = UserTesting(tested_date=validated_data.get("tested_date"),
                                      test_result=validated_data.get("test_result"), user=user)
                testing.save()
                instance.testing = testing
        instance.save()
        new_symtops = [each_sym for each_sym in symptoms if not each_sym.isdigit()]
        new_symtopsdigits = [each_sym for each_sym in symptoms if each_sym.isdigit()]
        for i in new_symtops:
            p, created = Symptoms.objects.get_or_create(name=i)
            if created == True:
                sym = Symptoms.objects.get(name=i)
                new_symtopsdigits.append(sym.id)
            else:
                sym = Symptoms.objects.get(name=i)
                new_symtopsdigits.append(sym.id)
        if new_symtopsdigits:
            instance.symptoms.clear()
            instance.symptoms.add(*new_symtopsdigits)
        else:
            instance.symptoms.clear()
        user.last_updated = timezone.now()
        user.save()
        if validated_data.get("test_result") == "Positive":
            if validated_data.get("data_started"):
                UserLocations.objects.filter(user=user, location_date__gte=validated_data.get("data_started")).update(
                    is_infected=True)
                location = UserLocations.objects.filter(user=user,
                                                        location_date__gte=validated_data.get("data_started"))
                for loc in location:
                    delta = datetime.timedelta(hours=3)
                    start = (datetime.datetime.combine(datetime.date(9999, 1, 1), loc.from_time) - delta).time()
                    end = (datetime.datetime.combine(datetime.date(9999, 1, 1), loc.to_time) + delta).time()
                    UserLocations.objects.filter(location_date=loc.location_date, location=loc.location,
                                                 from_time__gte=start, to_time__lte=end).update(is_infected=True)
                    effect_location = UserLocations.objects.filter(location_date=loc.location_date,
                                                                   location=loc.location, from_time__gte=start,
                                                                   to_time__lte=end)
                    if effect_location:
                        for effect in effect_location:
                            try:
                                location_user = User.objects.get(id=effect.user.id)
                                location_user.location_exposure += 1
                                location_user.save()
                            except:
                                pass
                    user.risk_level = True
                    user.save()

                contacts = UserContacts.objects.filter(user=user, date_contacted__range=[
                    validated_data.get("data_started") - datetime.timedelta(days=15),
                    validated_data.get("data_started") + datetime.timedelta(days=15)])
                UserContacts.objects.filter(user=user, date_contacted__range=[
                    validated_data.get("data_started") - datetime.timedelta(days=15),
                    validated_data.get("data_started") + datetime.timedelta(days=15)]).update(is_infected=True)
                for con in contacts:
                    try:
                        contact_user = User.objects.get(phone_number=con.phone_number)
                        if user != contact_user:
                            contact_user.contact_exposure += 1
                        contact_user.save()
                        user.risk_level = True
                        user.save()
                    except:
                        user.risk_level = True
                        user.save()
                flight = FlightDetails.objects.filter(user=user, date_journey__range=[
                    validated_data.get("data_started") - datetime.timedelta(days=15),
                    validated_data.get("data_started") + datetime.timedelta(days=15)])
                FlightDetails.objects.filter(user=user, date_journey__range=[
                    validated_data.get("data_started") - datetime.timedelta(days=15),
                    validated_data.get("data_started") + datetime.timedelta(days=15)]).update(is_infected=True)
                for fli in flight:
                    effect_flight_user = FlightDetails.objects.filter(date_journey=fli.date_journey,
                                                                      flight=fli.flight, flight_no=fli.flight_no)
                    if effect_flight_user:
                        for effect in effect_flight_user:
                            try:
                                flight_user = User.objects.get(id=effect.user.id)
                                flight_user.flight_exposure += 1
                                flight_user.save()
                            except:
                                pass
                    user.risk_level = True
                    user.save()
        else:
            if validated_data.get("data_started"):
                UserLocations.objects.filter(user=user, location_date__gte=validated_data.get("data_started")).update(
                    is_infected=False)
                location = UserLocations.objects.filter(user=user,
                                                        location_date__gte=validated_data.get("data_started"))
                for loc in location:
                    delta = datetime.timedelta(hours=3)
                    start = (datetime.datetime.combine(datetime.date(9999, 1, 1), loc.from_time) - delta).time()
                    end = (datetime.datetime.combine(datetime.date(9999, 1, 1), loc.to_time) + delta).time()
                    effect_location = UserLocations.objects.filter(location_date=loc.location_date,
                                                                   location=loc.location, from_time__gte=start,
                                                                   to_time__lte=end)
                    if effect_location:
                        for effect in effect_location:
                            try:
                                location_user = User.objects.get(id=effect.user.id)
                                location_user.location_exposure -= 1
                                report = UserReport.objects.filter(user=location_user).first()
                                if user == location_user:
                                    location_user.is_infected = False
                                if report and report.test_result == "Negative":
                                    location_user.is_infected = False
                                if not report:
                                    location_user.is_infected = False
                                location_user.save()
                            except:
                                pass
                    user.risk_level = False
                    user.save()

                contacts = UserContacts.objects.filter(user=user, date_contacted__range=[
                    validated_data.get("data_started") - datetime.timedelta(days=15),
                    validated_data.get("data_started") + datetime.timedelta(days=15)])
                UserContacts.objects.filter(user=user, date_contacted__range=[
                    validated_data.get("data_started") - datetime.timedelta(days=15),
                    validated_data.get("data_started") + datetime.timedelta(days=15)]).update(is_infected=False)
                for con in contacts:
                    try:
                        contact_user = User.objects.get(phone_number=con.phone_number)
                        contact_user.contact_exposure -= 1
                        contact_user.save()
                        user.risk_level = False
                        user.save()
                    except:
                        user.risk_level = False
                        user.save()
                flight = FlightDetails.objects.filter(user=user, date_journey__range=[
                    validated_data.get("data_started") - datetime.timedelta(days=15),
                    validated_data.get("data_started") + datetime.timedelta(days=15)])
                FlightDetails.objects.filter(user=user, date_journey__range=[
                    validated_data.get("data_started") - datetime.timedelta(days=15),
                    validated_data.get("data_started") + datetime.timedelta(days=15)]).update(is_infected=False)
                for fli in flight:
                    effect_flight_user = FlightDetails.objects.filter(date_journey=fli.date_journey,
                                                                      flight=fli.flight, flight_no=fli.flight_no)
                    if effect_flight_user:
                        for effect in effect_flight_user:
                            try:
                                flight_user = User.objects.get(id=effect.user.id)
                                flight_user.flight_exposure -= 1
                                flight_user.save()
                            except:
                                pass
                    user.risk_level = False
                    user.save()
            else:
                UserLocations.objects.filter(user=user).update(
                    is_infected=False)
                UserContacts.objects.filter(user=user).update(is_infected=False)
                FlightDetails.objects.filter(user=user).update(is_infected=False)
        last_updated = Lastupdated(updated_time=timezone.now())
        last_updated.save()
        return return_data


class UserReportStatusSerializer(serializers.ModelSerializer):
    """
    User Report Status Retrieve Update Serializer
    """
    class Meta:
        model = UserReport
        fields = "__all__"
        read_only_fields = ("id", "user")


class ForgotPasswordSerializer(Serializer):
    """
    Serializer for Mobile forgot password
    """
    phone_number = CharField(label="Enter Phone Number")
    otp = CharField(label="Enter OTP", allow_blank=True, allow_null=True, required=False)

    def validate(self, data):
        phone_number = data.get("phone_number", None)
        qs = User.objects.filter(phone_number=phone_number)
        if not qs.exists():
            raise ValidationError("The user with %s not found" % (phone_number))
        user_obj = qs.first()
        if not user_obj.phone_number:
            raise ValidationError("There is no mobile number associated with this user")
        return data


class ResetPasswordSerializer(Serializer):
    """
    Serializer for Reset Password
    """
    new_password = CharField(write_only=True)
    confirm_password = CharField(write_only=True)

    def validate(self, data):
        new_password = data.get("new_password", None)
        confirm_password = data.get("confirm_password", None)
        user = self.context.get('user')
        if new_password != confirm_password:
            raise ValidationError('Passwords Must Match')

        if not re.match(r"^(?=.*[\d])(?=.*[A-Z])(?=.*[a-z])(?=.*[~!@#$%^&*()_+\.])[\w\d~!@#$%^&*()_+\.]{6,}$",
                        new_password):
            raise ValidationError(
                'Your password has to be at least 6 characters long.'
                ' Must contain at least one lower case letter, '
                'one upper case letter, one digit. at least one special character'
                ' ~!@#$%^&*()_+.')
        user.set_password(new_password)
        user.save()
        return data


class MobileResetPasswordSerializer(ResetPasswordSerializer):
    """
    Serializer for  reset password.
    """
    phone_number = CharField(label="Enter Phone  Number")


class UserReportListSerializer(ModelSerializer):
    """
    User Report serializer
    """
    symptoms = SymptomsSerializer(many=True)

    class Meta:
        model = UserReport
        fields = "__all__"
        read_only_fields = ("id", "user", "symptoms",)


class MobilesNumberSerializer(Serializer):
    """
    Serializer to send SMS OTP
    """
    email = EmailField(label='Email Address')
    mobile_number = CharField(label='Mobile Number')

    def validate(self, data):
        email = data.get("email", None)
        mobile_number = data.get("mobile_number", None)
        if not email:
            raise ValidationError('email can not be null')
        if not mobile_number:
            raise ValidationError('Mobile number can not be null')
        if User.objects.filter(phone_number=mobile_number).exists():
            if not User.objects.filter(email=email, phone_number=mobile_number).exists():
                raise ValidationError('This mobile number has already registered')

        return data


class UserSerializer(ModelSerializer):
    """
    status detail serializer
    """

    class Meta:
        model = User
        fields = [
            'last_updated',
        ]


class LastUpdatedListSerializer(ModelSerializer):
    """
    User Report serializer
    """

    class Meta:
        model = Lastupdated
        fields = "__all__"
        read_only_fields = ("id", "date_created",)


class ScreeningAnswerSerializer(ModelSerializer):
    """
    ScreeningAnswer serializer
    """
    class Meta:
        model = ScreeningAnswer
        fields = '__all__'


class ScreeningQuestionOptionSerializer(ModelSerializer):
    class Meta:
        model = ScreeningQuestionOption
        fields = '__all__'


class ScreeningQuestionDetailSerializer(ModelSerializer):
    """
    ScreeningQuestion serializer
    """
    options = ScreeningQuestionOptionSerializer(many=True)

    class Meta:
        model = ScreeningQuestion
        fields = '__all__'


class ScreeningQuestionSerializer(ModelSerializer):
    class Meta:
        model = ScreeningQuestion
        fields = '__all__'


class ScreeningDetailSerializer(ModelSerializer):
    """
    Screening serializer for retrieve action
    """
    questions = ScreeningQuestionDetailSerializer(many=True)

    class Meta:
        model = Screening
        fields = '__all__'


class ScreeningSerializer(ModelSerializer):
    class Meta:
        model = Screening
        fields = '__all__'


class ScreeningUserDetailSerializer(ModelSerializer):
    """
    ScreeningUser serializer
    """
    answers = ScreeningAnswerSerializer(many=True)

    class Meta:
        model = ScreeningUser
        fields = '__all__'


class ScreeningUserSerializer(ModelSerializer):
    class Meta:
        model = ScreeningUser
        fields = '__all__'
