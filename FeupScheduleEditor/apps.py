from django.apps import AppConfig

class FeupScheduleEditorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'FeupScheduleEditor'

    def ready(self):
        import FeupScheduleEditor.templatetags.my_filters
