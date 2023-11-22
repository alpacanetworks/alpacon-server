from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from iam.models import User, Group
from api.password_reset.models import ResetToken


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['id', 'username', 'first_name', 'last_name', 'email', 'uid', 'tags', 'has_usable_password', 'is_active', 'is_staff', 'is_superuser', 'date_joined', 'last_login']
    list_filter = ['is_active', 'is_staff', 'is_superuser']
    search_fields = ['id', 'username', 'first_name', 'last_name', 'email']
    actions = ['reset_password']
    
    def reset_password(self, reqeust, queryset):
        for obj in queryset:
            token = ResetToken.objects.create_tokens(email=obj.email)
            token.send_email()
    reset_password.short_description = _('Send password reset links for selected users.')


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'display_name', 'gid', 'tags', 'is_ldap_group', 'added_at', 'updated_at']