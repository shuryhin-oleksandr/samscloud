from django.contrib import admin
from .models import User, MobileOtp, ForgotPasswordOTP


class UserModelAdmin(admin.ModelAdmin):
    search_fields = ('email', 'first_name')
    list_display = ['email', 'first_name', 'last_name', 'is_verified']


class MobileOtpModelAdmin(admin.ModelAdmin):
    search_fields = ('user__first_name',)
    list_display = ['user', 'date_created']


class ForgotPasswordOTPModelAdmin(admin.ModelAdmin):
    search_fields = ('user__first_name',)
    list_display = ['user', 'date_created']

admin.site.register(User, UserModelAdmin)
admin.site.register(MobileOtp, MobileOtpModelAdmin)
admin.site.register(ForgotPasswordOTP, ForgotPasswordOTPModelAdmin)