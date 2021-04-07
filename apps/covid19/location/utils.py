from apps.covid19.location.models import UserLocations, UserLocationTagging


def truncate_coordinate(value, digits):
    return int(float(value) * 10 ** digits) / 10.0 ** digits


def create_tagging_location(validated_data, user, start, latitude, longitude, is_infected=False):
    user_location = UserLocations.objects.filter(location_date=validated_data['location_date'],
                                                 latitude__contains=latitude,
                                                 longitude__contains=longitude,
                                                 user=user,
                                                 to_time__gte=start).order_by('-to_time').last()
    if user_location is None:
        user_location = UserLocations.objects.create(user=user, **validated_data, is_infected=is_infected)
        UserLocationTagging.objects.create(user_location=user_location,
                                           from_time=validated_data[
                                               'from_time'],
                                           to_time=validated_data['to_time'],
                                           is_infected=is_infected)
    else:
        user_location.to_time = validated_data['to_time']
        user_location.save()
        UserLocationTagging.objects.create(user_location=user_location,
                                           from_time=validated_data['from_time'],
                                           to_time=validated_data['to_time'],
                                           is_infected=is_infected)
    return user_location
