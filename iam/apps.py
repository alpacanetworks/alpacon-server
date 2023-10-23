from django.apps import AppConfig


class IAMConfig(AppConfig):
    name = 'iam'

    def ready(self) -> None:
        import iam.signals
