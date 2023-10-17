from django.contrib import admin
from django.utils.translation import gettext_lazy as  _

from servers.models import Server


@admin.register(Server)
class ServerAdmin(admin.ModelAdmin):
    list_display = ('name', 'commissioned', 'version', 'osquery_version', 'added_at', 'updated_at', 'deleted_at')
    search_fields = ('name',)
    actions = ['update_information', 'upgrade_servers', 'restart_servers', 'quit_servers', 'update_system', 'reboot_system']

    def update_information(self, request, queryset):
        for server in queryset.filter(connected=True):
            server.update_information()

    def upgrade_servers(self, request, queryset):
        for server in queryset.filter(connected=True):
            server.upgrade(requested_by=request.user)

    def restart_servers(self, request, queryset):
        for server in queryset.filter(connected=True):
            server.restart(requested_by=request.user)

    def quit_servers(self, request, queryset):
        for server in queryset.filter(connected=True):
            server.quit(requested_by=request.user)

    def update_system(self, request, queryset):
        for server in queryset.filter(connected=True):
            server.update_system(requested_by=request.user)

    def reboot_system(self, request, queryset):
        for server in queryset.filter(connected=True):
            server.reboot_system(requested_by=request.user)
