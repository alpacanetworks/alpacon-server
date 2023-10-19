from django.apps import AppConfig


class ServersConfig(AppConfig):
    name = 'servers'

    def ready(self):
        import servers.signals
