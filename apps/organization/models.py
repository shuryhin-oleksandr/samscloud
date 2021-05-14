from django.db import models
from django.contrib.auth import get_user_model
from apps.accounts.models import TimeStampedModel
from datetime import datetime
from django.dispatch import receiver
from django.db.models import signals
from django.contrib.gis.db import models as geo_models
from django.db.models import Manager as GeoManager
import uuid

from django.core.exceptions import NON_FIELD_ERRORS

# Create your models here.
User = get_user_model()
ROLE = (
    ('Owner', 'Owner'),
)
WHO_CAN_JOIN = (
    ('Public', 'Public'),
    ('Private', 'Private')
)

RELATIONSHIP = (
    ('Mother', 'Mother'),
    ('Father', 'Father'),
    ('Brother', 'Brother'),
    ('Sister', 'Sister'),
    ('Wife', 'Wife'),
    ('Husband', 'Husband'),
    ('Family Member', 'Family Member'),
    ('Friend', 'Friend'),
    ('Other', 'Other')
    )

STATUS = (
    ('Save', 'Save'),
    ('Update', 'Update'),
    ('Inactive', 'Inactive'),
)

EMERGENCY_CONTACT_STATUS = (
    ('Pending', 'Pending'),
    ('Accepted', 'Accepted'),
    ('Rejected', 'Rejected'),
)

CONTACT_TYPE = (
    ('Emergency', 'Emergency'),
    ('Family', 'Family'),
)


class OrganizationType(models.Model):
    type_name = models.CharField(max_length=255)
    is_active = models.BooleanField()


class OrganizationProfile(TimeStampedModel):
    parent_organization = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True,
                                            related_name='parent')
    organization_name = models.CharField(max_length=100, unique=True)
    address = models.TextField(blank=True, null=True)
    contact_name = models.CharField(max_length=100, blank=True, null=True)
    role = models.CharField(max_length=15, choices=ROLE, blank=True, null=True)
    email = models.EmailField(max_length=50, blank=True, null=True)
    latitude = models.CharField(max_length=60, null=True, blank=True)
    longitude = models.CharField(max_length=60, blank=True, null=True)
    logo = models.ImageField(upload_to='organization-images', blank=True, null=True)
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    pro_code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True, null=True)
    organization_email = models.EmailField(blank=True, null=True)
    organization_type = models.ForeignKey(OrganizationType, blank=True, null=True, on_delete=models.SET_NULL)
    who_can_join = models.CharField(choices=WHO_CAN_JOIN, max_length=20, null=True, blank=True)
    url = models.CharField(blank=True, null=True, max_length=70)
    is_dispatch = models.BooleanField(default=False)
    is_alert_sams = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    number_of_floors = models.CharField(max_length=20, null=True, blank=True)
    shinobi_authkey = models.CharField(max_length=100, null=True, blank=True)
    shinobi_group_key = models.CharField(max_length=100, null=True, blank=True)
    is_covid_active = models.BooleanField(default=False)

    def __str__(self):
        return self.organization_name


class UserOrganization(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    organization = models.ForeignKey(OrganizationProfile, on_delete=models.CASCADE)
    is_muted = models.BooleanField(default=False)
    is_show_covid_info = models.BooleanField(default=False)

    def __str__(self):
        return self.user.first_name + self.organization.organization_name


@receiver(signals.pre_save, sender=OrganizationProfile)
def create_pro_code(sender, instance, **kwargs):
    if not instance.pro_code:
        try:
            current_id = OrganizationProfile.objects.latest('id').id
        except:
            current_id = 1
        date_string = str(datetime.today().date().day) + str(current_id + 1)
        organization_name = instance.organization_name
        organization_name = organization_name.replace(" ", "")
        if len(organization_name) < 4:
            pro_code = instance.organization_name + date_string
        else:
            pro_code = organization_name[:4] + date_string
        qs = OrganizationProfile.objects.filter(pro_code=pro_code).order_by("-id")
        if qs.exists():
            pro_code = "%s-%s" % (pro_code, qs.first().id)
            instance.pro_code = pro_code
        else:
            instance.pro_code = pro_code


class OrganizationContact(TimeStampedModel):
    organization = models.ForeignKey(OrganizationProfile, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=50)
    contact_role = models.CharField(max_length=20, choices=ROLE)
    phone_number = models.CharField(max_length=20)
    email = models.EmailField()
    uuid = models.UUIDField(editable=False, unique=True, blank=True, null=True, default=uuid.uuid4)
    latitude = models.CharField(max_length=20, blank=True, null=True)
    longitude = models.CharField(max_length=20, blank=True, null=True)
    altitude = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return self.organization.organization_name


class EmergencyContact(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=20)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    relationship = models.CharField(max_length=20, choices=RELATIONSHIP, blank=True, null=True)
    status = models.CharField(max_length=20, choices=EMERGENCY_CONTACT_STATUS, default="Pending")
    contact_type = models.CharField(max_length=20, blank=True, null=True, choices=CONTACT_TYPE)
    uuid = models.UUIDField(editable=False, unique=True, blank=True, null=True, default=uuid.uuid4)
    latitude = models.CharField(max_length=20, blank=True, null=True)
    longitude = models.CharField(max_length=20, blank=True, null=True)
    altitude = models.CharField(max_length=20, blank=True, null=True)
    request_checkin_updated = models.DateTimeField(blank=True, null=True)
    request_checkin_latitude = models.CharField(max_length=20, blank=True, null=True)
    request_checkin_longitude = models.CharField(max_length=20, blank=True, null=True)
    request_checkin_address = models.CharField(max_length=200, blank=True, null=True)


    def __str__(self):
        return self.name


class OrganizationAddress(TimeStampedModel):
    """
    Organization Address
    """
    organization = models.OneToOneField(OrganizationProfile, on_delete=models.CASCADE)
    street_number = models.CharField(max_length=50, null=True, blank=True)
    street_name = models.CharField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    zip_code = models.CharField(max_length=50, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    address = models.TextField(blank=True, null=True)
    is_manually_added = models.BooleanField(default=False)

    def __str__(self):
        return '{} | {}'.format(self.organization.organization_name, self.country if self.country else '')


class OrganizationFloors(TimeStampedModel):
    organization = models.ForeignKey(OrganizationProfile, on_delete=models.CASCADE)
    altitude = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)
    floor_number = models.IntegerField()

    def __str__(self):
        return self.organization.organization_name + "-" + str(self.floor_number)


class OrganizationGeoFence(models.Model):
    organization = models.OneToOneField(OrganizationProfile, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    co_ordinates = geo_models.PolygonField()
    is_active = models.BooleanField(default=True)
    objects = GeoManager()
    zone_count = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.organization.organization_name


class ZoneDocument(models.Model):
    name = models.CharField(max_length=50, blank=True, null=True)
    document = models.FileField(upload_to='zone/documents/', blank=True, null=True)

    def __str__(self):
        return self.name

class Zone(TimeStampedModel):
    name = models.CharField(max_length=50)
    user = models.ForeignKey(User, blank=True, null=True, on_delete=models.SET_NULL)
    organization = models.ForeignKey(OrganizationProfile, blank=True, null=True, on_delete=models.CASCADE)
    center_point = geo_models.PointField()
    point1 = geo_models.PointField(null=True, blank=True)
    point2 = geo_models.PointField(null=True, blank=True)
    point3 = geo_models.PointField(null=True, blank=True)
    point4 = geo_models.PointField(null=True, blank=True)


    objects = GeoManager()

    def __str__(self):
        return self.name + "-" + self.organization.organization_name


class ZoneCCTV(models.Model):
    name = models.CharField(max_length=50)
    monitor_id = models.CharField(max_length=50, null=True, blank=True)
    zone = models.ForeignKey(Zone, null=True, blank=True, on_delete=models.CASCADE)
    floor = models.ForeignKey(OrganizationFloors, null=True, blank=True, on_delete=models.CASCADE)
    latitude = models.CharField(max_length=60, null=True, blank=True)
    longitude = models.CharField(max_length=60, blank=True, null=True)
    user_name = models.CharField(max_length=60, blank=True, null=True)
    password = models.CharField(max_length=60, blank=True, null=True)
    ip_address = models.CharField(max_length=60, blank=True, null=True)

    def __str__(self):
        return self.name


class ZoneFloor(TimeStampedModel):
    name = models.CharField(max_length=50, blank=True, null=True)
    organization_zone = models.ForeignKey(Zone, on_delete=models.CASCADE)
    floor = models.ForeignKey(OrganizationFloors, on_delete=models.CASCADE, blank=True, null=True)
    cctv_camera = models.ManyToManyField(ZoneCCTV, blank=True)
    document = models.ManyToManyField(ZoneDocument, blank=True)

    def __str__(self):
        return self.name


class OrganizationMessage(models.Model):
    organization = models.ForeignKey(OrganizationProfile, on_delete=models.CASCADE, related_name="messageorganization")
    title = models.CharField(max_length=255, null=True, blank=True)
    details = models.TextField(blank=True)
    file_upload = models.FileField(verbose_name="organization file", blank=True, upload_to='static/media/')
    is_read = models.BooleanField(default=False, blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.organization.organization_name