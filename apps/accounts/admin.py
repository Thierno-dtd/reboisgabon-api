from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, PasswordResetToken, TOTPDevice


class UserAdmin(BaseUserAdmin):
    ordering = ['-date_joined']
    list_display = ['email', 'first_name', 'last_name', 'role', 'is_active', 'two_fa_enabled']
    list_filter = ['role', 'is_active', 'two_fa_enabled']
    search_fields = ['email', 'first_name', 'last_name']
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Infos personnelles', {'fields': ('first_name', 'last_name', 'role')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'two_fa_enabled')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'role', 'password1', 'password2'),
        }),
    )


admin.site.register(User, UserAdmin)
admin.site.register(PasswordResetToken)
admin.site.register(TOTPDevice)