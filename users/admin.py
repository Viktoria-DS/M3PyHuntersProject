from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from users.models import User


@admin.register(User)
class UserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        (
            'Additional information',
            {
                'fields': ('avatar', 'city', 'address', 'phone'),
            },
        ),
    )
    readonly_fields = ('last_login', 'date_joined')