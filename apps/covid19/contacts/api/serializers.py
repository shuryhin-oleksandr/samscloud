import datetime
from datetime import timedelta
from fcm_django.models import FCMDevice
from rest_framework.serializers import ModelSerializer

from apps.covid19.contacts.models import Symptoms, UserContacts, Disease, UserContactTagging
from apps.reports.models import NotificationHistory
from django.contrib.auth import get_user_model
from apps.accounts.api.utils import send_push_notification

from rest_framework.serializers import (
    CharField,
    IntegerField,
    DateField,
    TimeField,
    ReadOnlyField
)

User = get_user_model()


class SymptomsSerializer(ModelSerializer):
    """
    Symptoms serializer
    """

    class Meta:
        model = Symptoms
        fields = [
            'id',
            'name',
        ]


class DiseaseSerializer(ModelSerializer):
    """
    Symptoms serializer
    """

    class Meta:
        model = Disease
        fields = [
            'id',
            'name',
        ]


class UserContactSerializer(ModelSerializer):
    """
    User contact serializer
    """

    # user_contacted = IntegerField(required=False)

    class Meta:
        model = UserContacts
        fields = "__all__"
        read_only_fields = ("id", "user")

    def create(self, validated_data):
        request = self.context.get('request')
        report = self.context.get('report')
        user = request.user
        user_contacted = None
        # if 'user_contacted' in validated_data and validated_data['user_contacted'] is not None:
        #     if isinstance(validated_data['user_contacted'], dict):
        #         user_contacted = validated_data.pop('user_contacted')
        #         user_contacted_id = user_contacted['id']
        #     else:
        #         user_contacted_id = validated_data.pop('user_contacted')
        #         user_contacted = User.objects.get(id=user_contacted_id)
        if report and report.test_result == "Positive":
            if report.data_started and report.data_started - timedelta(days=15) <= validated_data[
                'date_contacted'] <= report.data_started + timedelta(days=15):
                try:
                    contact_user = User.objects.get(phone_number=validated_data['phone_number'])
                    if user != contact_user:
                        contact_user.contact_exposure += 1
                    contact_user.save()
                except:
                    pass
                user.risk_level = True
                user.save()
                return UserContacts.objects.create(user=user, user_contacted=user_contacted, is_infected=True,
                                                   **validated_data)
        else:
            effect_contact = UserContacts.objects.filter(phone_number=validated_data.get("phone_number"),
                                                         date_contacted__range=[
                                                             validated_data.get(
                                                                 "date_contacted") - timedelta(days=15),
                                                             validated_data.get(
                                                                 "date_contacted") + timedelta(days=15)],
                                                         is_infected=True)
            if effect_contact:
                user.risk_level = True
                user.contact_exposure += 1
                user.save()
                return UserContacts.objects.create(user=user, user_contacted=user_contacted, is_infected=True,
                                                   **validated_data)
            else:
                try:
                    contact_user = User.objects.get(phone_number=validated_data['phone_number'])
                    if user != contact_user:
                        user.risk_level = True
                        user.contact_exposure += 1
                        user.save()
                        return UserContacts.objects.create(user=user, user_contacted=user_contacted, is_infected=True,
                                                           **validated_data)
                except:
                    pass
        return UserContacts.objects.create(user=user, user_contacted=user_contacted, **validated_data)


class UserContactTaggingSerializer(ModelSerializer):
    """
    User contact tagging serializer
    """

    latitude = CharField(max_length=60, required=False)
    longitude = CharField(max_length=60, required=False)
    from_time = TimeField(required=False)
    to_time = TimeField(required=False)
    date_contacted = DateField(format="%Y-%m-%d", required=False)

    class Meta:
        model = UserContactTagging
        fields = "__all__"
        read_only_fields = ("id", "user_contact", "is_infected")

    def create(self, validated_data):
        request = self.context.get('request')
        report = self.context.get('report')
        user = request.user
        contact_user = User.objects.get(id=request.data['user_contacted'])
        contact_phone = getattr(contact_user, 'phone_number', None)
        contact_name = getattr(contact_user, 'first_name', None)
        from_time = validated_data.pop('from_time')
        to_time = validated_data.pop('to_time')
        latitude = validated_data.get('latitude')
        longitude = validated_data.get('longitude')
        place_tag = validated_data.get('place_tag', None)
        today_contact = UserContacts.objects.filter(phone_number=contact_phone,
                                                    user_contacted=contact_user,
                                                    user=user,
                                                    date_contacted=validated_data.get(
                                                        "date_contacted")).last()
        if today_contact:
            delta = datetime.timedelta(minutes=4)
            start = (datetime.datetime.combine(datetime.date(9999, 1, 1),
                                               from_time) - delta).time()

            end = (datetime.datetime.combine(datetime.date(9999, 1, 1),
                                             to_time) + delta).time()
            active_tag = UserContactTagging.objects.filter(user_contact=today_contact,
                                                           from_time__gte=start,
                                                           to_time__lte=end).order_by('-to_time').last()
            if active_tag:
                active_tag.to_time = to_time
                active_tag.save()
                return active_tag
            morning_tag = UserContactTagging.objects.filter(user_contact=today_contact,
                                                            to_time__lte=start).order_by('-to_time').last()
            if morning_tag and morning_tag.is_infected is False:
                infected_contact = UserContacts.objects.filter(user=contact_user,
                                                               date_contacted=validated_data.get(
                                                                   "date_contacted"),
                                                               is_infected=True).last()
                if infected_contact:
                    user.risk_level = True
                    user.contact_exposure += 1
                    user.save()
                    qs = FCMDevice.objects.filter(user=user)
                    if qs.exists():
                        fcm_obj = qs.first()
                        data = {
                            "type": "high-risk-area"
                        }
                        message = "You came in contact with a user that reported being infected with Covid-19. " \
                                  "You may have contracted the virus and could be unknowingly spreading it. " \
                                  "Please quarantine for at least 14 days and test to confirm your status."
                        title = "High Risk Area"
                        send_push_notification.delay(fcm_obj.id, title, message, data)
                        history = NotificationHistory(user=user, requested_user=user,
                                                      attribute=data,
                                                      notification_type="high-risk-area", message=message,
                                                      title=title)
                        history.save()
                    user_contact = UserContacts.objects.create(user=user, name=contact_name,
                                                               phone_number=contact_phone, user_contacted=contact_user,
                                                               is_infected=True, is_tagged=True,
                                                               **validated_data)
                    return UserContactTagging.objects.create(user_contact=user_contact, from_time=from_time,
                                                             to_time=to_time, latitude=latitude,
                                                             longitude=longitude,
                                                             place_tag=place_tag,
                                                             is_infected=True)
            return UserContactTagging.objects.create(user_contact=today_contact, from_time=from_time,
                                                     to_time=to_time, latitude=latitude,
                                                     longitude=longitude,
                                                     place_tag=place_tag,
                                                     is_infected=today_contact.is_infected)

        if report and report.test_result == "Positive":
            if report.data_started and report.data_started - datetime.timedelta(days=15) <= validated_data[
                'date_contacted'] <= report.data_started + datetime.timedelta(days=15):
                try:
                    if user != contact_user:
                        contact_user.contact_exposure += 1
                    contact_user.save()
                except:
                    pass
                user.risk_level = True
                user.save()
                user_contact = UserContacts.objects.create(user=user, name=contact_name,
                                                           phone_number=contact_phone, user_contacted=contact_user,
                                                           is_infected=True, is_tagged=True,
                                                           **validated_data)
                return UserContactTagging.objects.create(user_contact=user_contact, from_time=from_time,
                                                         to_time=to_time, latitude=latitude, is_infected=True,
                                                         longitude=longitude,
                                                         place_tag=place_tag)
        else:
            effect_contact = UserContacts.objects.filter(phone_number=contact_phone,
                                                         user_contacted=contact_user,
                                                         date_contacted__range=[
                                                             validated_data.get(
                                                                 "date_contacted") - datetime.timedelta(days=15),
                                                             validated_data.get(
                                                                 "date_contacted") + datetime.timedelta(days=15)],
                                                         is_infected=True)
            if contact_user.risk_level or effect_contact and user != contact_user:
                user.risk_level = True
                user.contact_exposure += 1
                user.save()
                user_contact = UserContacts.objects.create(user=user, name=contact_name,
                                                           phone_number=contact_phone,
                                                           user_contacted=contact_user,
                                                           is_infected=True, is_tagged=True,
                                                           **validated_data)
                qs = FCMDevice.objects.filter(user=user)
                if qs.exists():
                    fcm_obj = qs.first()
                    data = {
                        "type": "high-risk-area"
                    }
                    message = "You came in contact with a user that reported being infected with Covid-19. " \
                              "You may have contracted the virus and could be unknowingly spreading it. " \
                              "Please quarantine for at least 14 days and test to confirm your status."
                    title = "High Risk Area"
                    send_push_notification.delay(fcm_obj.id, title, message, data)
                    history = NotificationHistory(user=user, requested_user=user,
                                                  attribute=data,
                                                  notification_type="high-risk-area", message=message,
                                                  title=title)
                    history.save()
                return UserContactTagging.objects.create(user_contact=user_contact, from_time=from_time,
                                                         to_time=to_time, latitude=latitude, is_infected=True,
                                                         longitude=longitude,
                                                         place_tag=place_tag)
            else:
                try:
                    if user != contact_user:
                        user_contact = UserContacts.objects.create(user=user, name=contact_name,
                                                                   phone_number=contact_phone,
                                                                   user_contacted=contact_user, is_tagged=True,
                                                                   **validated_data)
                        return UserContactTagging.objects.create(user_contact=user_contact, from_time=from_time,
                                                                 to_time=to_time, latitude=latitude,
                                                                 longitude=longitude,
                                                                 place_tag=place_tag)
                except:
                    pass
        user_contact = UserContacts.objects.create(user=user, name=contact_name,
                                                   phone_number=contact_phone,
                                                   user_contacted=contact_user, is_tagged=True,
                                                   **validated_data)
        return UserContactTagging.objects.create(user_contact=user_contact, from_time=from_time,
                                                 to_time=to_time, latitude=latitude, longitude=longitude,
                                                 place_tag=place_tag)
