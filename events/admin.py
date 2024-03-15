from django.contrib import admin

from events.models import *


@admin.register(Command)
class CommandAdmin(admin.ModelAdmin):
    list_display = ('server', 'shell', 'line', 'scheduled_at', 'acked_at', 'handled_at', 'success', 'requested_by')
    list_filter = ('requested_by', 'shell', 'server', 'scheduled_at')
    readonly_fields = ('success', 'result', 'added_at', 'delivered_at', 'acked_at', 'handled_at')
    search_fields = ('line',)
    date_heirarchy = 'scheduled_at'
    ordering = ['-scheduled_at']
    actions = ['retry_commands']

    def save_model(self, request, obj, form, change):
        if obj.id is None and obj.requested_by is None:
            obj.requested_by = request.user
        super().save_model(request, obj, form, change)

    def retry_commands(self, request, queryset):
        for command in queryset:
            command.retry()
