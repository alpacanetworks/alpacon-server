from django.contrib import admin

from wsutils.models import *


@admin.register(WebSocketClient)
class WebSocketClientAdmin(admin.ModelAdmin):
    list_display = ('id', 'ip', 'concurrent', 'added_at', 'updated_at')
    ordering = ['-updated_at']


@admin.register(WebSocketSession)
class WebSocketSessionAdmin(admin.ModelAdmin):
    list_display = ('client', 'channel_id', 'remote_ip', 'added_at', 'updated_at', 'deleted_at')
    search_fields = ['remote_ip']
    ordering = ['-updated_at']
