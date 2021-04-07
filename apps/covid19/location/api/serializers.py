import datetime
from django.utils import timezone
from rest_framework.fields import DateField
from rest_framework.serializers import ModelSerializer
from apps.accounts.models import User
from apps.covid19.covid_accounts.models import UserReport, Lastupdated

from apps.covid19.contacts.models import UserContacts
from apps.covid19.location.models import UserLocations, GlobalLocations, AssistanceLocations, UserLocationTagging
from apps.covid19.location.utils import create_tagging_location, truncate_coordinate


class UserLocationSerializer(ModelSerializer):
    """
    User location serializer
    """

    class Meta:
        model = UserLocations
        fields = "__all__"
        read_only_fields = ("id", "user", "is_infected",)

    def to_representation(self, instance):
        data = super(UserLocationSerializer, self).to_representation(instance)
        data.update({"count": UserLocations.objects.filter(location=instance.location).count(),
                     "exposure": UserLocations.objects.filter(location=instance.location, is_infected=True).values_list(
                         'user').distinct().count(),
                     })
        if UserLocations.objects.filter(location=instance.location, is_infected=True):
            data.update({"first_exposure_date": UserLocations.objects.filter(location=instance.location,
                                                                             is_infected=True).earliest(
                'location_date').location_date,
                         "latest_exposure_date": UserLocations.objects.filter(location=instance.location,
                                                                              is_infected=True).latest(
                             'location_date').location_date})
        return data

    def create(self, validated_data):
        request = self.context.get('request')
        report = self.context.get('report')
        user = request.user
        delta = datetime.timedelta(minutes=10)
        start = (datetime.datetime.combine(datetime.date(9999, 1, 1),
                                           validated_data['from_time']) - delta).time()

        end = (datetime.datetime.combine(datetime.date(9999, 1, 1),
                                         validated_data['to_time']) + delta).time()
        last_updated = Lastupdated(updated_time=timezone.now())
        last_updated.save()
        latitude = truncate_coordinate(validated_data['latitude'], 4)
        longitude = truncate_coordinate(validated_data['longitude'], 4)
        if report and report.test_result == "Positive":
            if report.data_started and report.data_started <= validated_data['location_date']:
                UserLocations.objects.filter(location_date=validated_data['location_date'],
                                             latitude__contains=latitude,
                                             longitude__contains=longitude,
                                             from_time__gte=start,
                                             to_time__lte=end).update(
                    is_infected=True)
                effect_location_user = UserLocations.objects.filter(
                    location_date=validated_data['location_date'],
                    latitude__contains=latitude,
                    longitude__contains=longitude,
                    from_time__gte=start,
                    to_time__lte=end
                )
                if effect_location_user:
                    for effect in effect_location_user:
                        try:
                            location_tags_count = UserLocationTagging.objects.filter(user_location=effect).count()
                            location_user = User.objects.get(id=effect.user.id)
                            if location_tags_count == 1:
                                location_user.location_exposure += 1
                            if user != location_user:
                                user_contacts = UserContacts.objects.filter(
                                    date_contacted=validated_data['location_date'],
                                    user=user, user_contacted=location_user)
                                if not user_contacts:
                                    location_user.contact_exposure += 1
                                    UserContacts.objects.create(user=user, user_contacted=location_user,
                                                                is_infected=True,
                                                                name=location_user.first_name,
                                                                phone_number=location_user.phone_number,
                                                                latitude=validated_data['latitude'],
                                                                longitude=validated_data['longitude'],
                                                                location=validated_data['location'],
                                                                date_contacted=validated_data['location_date'],
                                                                is_tagged=True)
                                    location_user.save()
                        except:
                            pass
                user.risk_level = True
                user.save()
                if 'place_tag' in validated_data and validated_data['place_tag'] is not None:
                    return create_tagging_location(validated_data, user, start, latitude, longitude, is_infected=True)
                return UserLocations.objects.create(user=user, is_infected=True, **validated_data)
            if validated_data['place_tag'] is not None:
                return create_tagging_location(validated_data, user, start, latitude, longitude)
            return UserLocations.objects.create(user=user, **validated_data)
        else:
            infected_location = UserLocations.objects.filter(
                location_date=validated_data['location_date'],
                latitude__contains=latitude, longitude__contains=longitude, is_infected=True)
            infected_data = []
            if infected_location:
                for infect in infected_location:
                    delta = datetime.timedelta(minutes=8)
                    start = (datetime.datetime.combine(datetime.date(9999, 1, 1),
                                                       infect.from_time) - delta).time()
                    end = (datetime.datetime.combine(datetime.date(9999, 1, 1),
                                                     infect.to_time) + delta).time()

                    if start < end:
                        if validated_data['from_time'] >= start and validated_data[
                            'from_time'] <= end:
                            infected_data.append(infect)
                            # infect.user.location_exposure += 1

                    else:  # Over midnight
                        if validated_data['from_time'] >= start or validated_data[
                            'from_time'] <= end:
                            infected_data.append(infect)

        if infected_data:
            for infect in infected_data:
                location_tags_count = UserLocationTagging.objects.filter(user_location=infect).count()
                if location_tags_count == 1:
                    user.location_exposure += 1
                if user != infect.user:
                    user_contacts = UserContacts.objects.filter(
                        date_contacted=validated_data['location_date'],
                        user=user, user_contacted=infect.user)
                    if not user_contacts:
                        user.contact_exposure += 1
                        UserContacts.objects.create(user=user, user_contacted=infect.user, is_infected=True,
                                                    name=infect.user.first_name,
                                                    phone_number=infect.user.phone_number,
                                                    latitude=validated_data['latitude'],
                                                    longitude=validated_data['longitude'],
                                                    location=validated_data['location'],
                                                    date_contacted=validated_data['location_date'],
                                                    is_tagged=True)
            user.save()
            if 'place_tag' in validated_data and validated_data['place_tag'] is not None:
                return create_tagging_location(validated_data, user, start, latitude, longitude, is_infected=True)
            return UserLocations.objects.create(user=user, is_infected=True, **validated_data)
        if 'place_tag' in validated_data and validated_data['place_tag'] is not None:
            return create_tagging_location(validated_data, user, start, latitude, longitude)
        return UserLocations.objects.create(user=user, **validated_data)


class UserLocationUpdateSerializer(ModelSerializer):
    """
    User location update serializer
    """

    class Meta:
        model = UserLocations
        fields = "__all__"
        read_only_fields = ("id", "user", "is_infected")

    def update(self, instance, validated_data):
        return_data = validated_data.copy()
        instance.location = validated_data.get("location")
        instance.Country_Region = validated_data.get("Country_Region")
        instance.City = validated_data.get("City")
        instance.Province_State = validated_data.get("Province_State")
        instance.location_date = validated_data.get("location_date")
        instance.latitude = validated_data.get("latitude")
        instance.longitude = validated_data.get("longitude")
        instance.from_time = validated_data.get("from_time")
        instance.to_time = validated_data.get("to_time")
        if validated_data.get('is_hidden') and instance.place_tag is not None:
            instance.is_hidden = True
            UserLocations.objects.filter(location_date=validated_data['location_date'],
                                         place_tag=validated_data['place_tag'],
                                         from_time__gte=validated_data.get("from_time"),
                                         to_time__lte=validated_data.get("to_time")).update(
                is_hidden=True)
        instance.save()
        return return_data


class GlobalLocationListSerializer(ModelSerializer):
    """
    Global location  list serializer
    """

    class Meta:
        model = GlobalLocations
        fields = ["Country_Region"]


class GlobalLocationDetailSerializer(ModelSerializer):
    """
    Global location Detail serializer
    """

    class Meta:
        model = GlobalLocations
        fields = "__all__"


class AssistanceLocationDetailsSerializer(ModelSerializer):
    """
     assistance location detail serializer
    """

    class Meta:
        model = AssistanceLocations
        fields = "__all__"
        read_only_fields = ("id", "date_created", "updated_at", "user")
