from django.contrib import admin

from api.apitoken.models import APIToken

@admin.register(APIToken)
class APITokenAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'enabled', 'added_at', 'updated_at', 'expires_at']
    list_filter = ['enabled']
    search_fields = ['id', 'user__username', 'user__first_name', 'user__last_name']
