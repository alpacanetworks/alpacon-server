from django.contrib import admin

from api.apiclient.models import APIClient


@admin.register(APIClient)
class APIClientAdmin(admin.ModelAdmin):
    list_display = ['id', 'ip', 'concurrent', 'owner', 'enabled', 'added_at', 'updated_at', 'expires_at']
    list_filter = ['concurrent', 'enabled']
    search_fields = ['id', 'ip', 'owner__ownername', 'owner__first_name', 'owner__last_name']
