from django.contrib import admin

from src.projects.models import Group, Project


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    search_fields = ("abbreviation__startswith",)


@admin.register(Project)
class GradeAdmin(admin.ModelAdmin):
    search_fields = ("name__startswith",)
    list_display = ("name",)
    list_filter = (
        "creator",
        "group",
    )
