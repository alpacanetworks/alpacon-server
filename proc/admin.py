import logging

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from proc.models import *


logger = logging.getLogger(__name__)


@admin.register(SystemInfo)
class SystemInfoAdmin(admin.ModelAdmin):
    list_display = ('server', 'hostname', 'uuid', 'cpu_type', 'cpu_subtype', 'cpu_brand', 'cpu_physical_cores', 'cpu_logical_cores', 'physical_memory', 'hardware_vendor', 'hardware_model', 'hardware_serial', 'computer_name', 'local_hostname')
    search_fields = ('hostname',)


@admin.register(OsVersion)
class OsVersionAdmin(admin.ModelAdmin):
    list_display = ('server', 'name', 'version', 'major', 'minor', 'patch', 'build', 'platform', 'platform_like')


@admin.register(SystemTime)
class SystemTimeAdmin(admin.ModelAdmin):
    list_display = ('server', 'datetime', 'timezone', 'uptime')


@admin.register(SystemUser)
class SystemUserAdmin(admin.ModelAdmin):
    list_display = ('server', 'uid', 'gid', 'username', 'description', 'directory', 'shell')
    search_fields = ('username',)


@admin.register(SystemGroup)
class SystemGroupAdmin(admin.ModelAdmin):
    list_display = ('server', 'gid', 'groupname')
    search_fields = ('groupname',)


@admin.register(Interface)
class InterfaceAdmin(admin.ModelAdmin):
    list_display = ('server', 'name', 'mac', 'type', 'flags')


@admin.register(InterfaceAddress)
class InterfaceAddressAdmin(admin.ModelAdmin):
    list_display = ('interface', 'address', 'mask', 'broadcast')


@admin.register(SystemPackage)
class InstalledSystemPackageAdmin(admin.ModelAdmin):
    list_display = ('server', 'name', 'version', 'source', 'arch', 'added_at')
    search_fields = ('name',)
    actions = ['uninstall_selected']

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def uninstall_selected(self, request, queryset):
        for package in queryset:
            logger.info('Deleting %s-%s from %s.', package.name, package.version, package.server)
            package.uninstall(request.user)
    uninstall_selected.short_description = _('Uninstall selected packages')


@admin.register(PythonPackage)
class InstalledPythonPackageAdmin(admin.ModelAdmin):
    list_display = ('server', 'name', 'version', 'added_at')
    search_fields = ('name',)
    actions = ['uninstall_selected']

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions
    
    def uninstall_selected(self, request, queryset):
        for package in queryset:
            logger.info('Deleting %s-%s from %s.', package.name, package.version, package.server)
            package.uninstall(request.user)
    uninstall_selected.short_description = _('Uninstall selected packages')


@admin.register(PythonVersion)
class PythonVersionAdmin(admin.ModelAdmin):
    list_display = ('server', 'python2', 'python3')
