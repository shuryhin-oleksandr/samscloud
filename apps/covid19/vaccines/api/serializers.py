import os
from rest_framework.serializers import ModelSerializer
from rest_framework import serializers

from apps.covid19.covid_accounts.models import UserReport
from apps.covid19.vaccines.models import UserVaccine, Dose, Manufacturer
from django.contrib.auth import get_user_model

User = get_user_model()


class DoseSerializer(ModelSerializer):
    """
    dose serializer
    """

    class Meta:
        model = Dose
        fields = "__all__"


class ManufacturerSerializer(ModelSerializer):
    """
    manufacturer serializer
    """

    class Meta:
        model = Manufacturer
        fields = "__all__"


class UserVaccineSerializer(ModelSerializer):
    """
    user vaccine serializer
    """
    manufacturer = ManufacturerSerializer(read_only=True)
    dosage = DoseSerializer(read_only=True)

    class Meta:
        model = UserVaccine
        fields = "__all__"
        read_only_fields = ("id", "user")


class UserVaccineUpdateSerializer(ModelSerializer):
    """
    user vaccine serializer
    """
    user = serializers.IntegerField()
    manufacturer = serializers.IntegerField()
    dosage = serializers.IntegerField()
    vaccinated_date = serializers.DateField(format="%Y-%m-%d", required=False)
    location = serializers.CharField(required=False, allow_blank=True, max_length=255)
    lot = serializers.CharField(required=False, allow_blank=True, max_length=100)
    is_reminded = serializers.BooleanField(default=False)
    file_upload = serializers.FileField(required=False)
    empty_file = serializers.BooleanField(required=False)

    class Meta:
        model = UserVaccine
        fields = "__all__"
        read_only_fields = ("id", "user")

    def update(self, instance, validated_data):
        """
        Update and return an existing `Snippet` instance, given the validated data.
        """
        return_data = validated_data.copy()
        manufacturer = Manufacturer.objects.filter(id=validated_data.get("manufacturer")).first()
        dosage = Dose.objects.filter(id=validated_data.get("dosage")).first()
        user = User.objects.filter(id=validated_data.get("user")).first()
        instance.location = validated_data.get("location")
        instance.dosage = dosage
        instance.manufacturer = manufacturer
        instance.user = user
        instance.lot = validated_data.get("lot")
        instance.vaccinated_date = validated_data.get("vaccinated_date")
        instance.is_reminded = validated_data.get('is_reminded', False)
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
        last_vaccine = UserVaccine.objects.filter(user=user).order_by('-vaccinated_date').last()
        if report is not None and instance.vaccinated_date > last_vaccine.vaccinated_date:
            report.vaccine = instance
            report.save()
        return return_data
