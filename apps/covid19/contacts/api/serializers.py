from datetime import timedelta
from rest_framework.serializers import ModelSerializer

from apps.covid19.contacts.models import Symptoms, UserContacts, Disease
from django.contrib.auth import get_user_model

from rest_framework.serializers import (
    CharField,
    IntegerField,
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
