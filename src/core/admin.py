from django.contrib import admin

from src.core.models import Group, Project


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    search_fields = ("abreviation__startswith",)


@admin.register(Project)
class GradeAdmin(admin.ModelAdmin):
    search_fields = ("project__startswith",)
    list_display = ("project",)
    list_filter = (
        "person",
        "group",
    )
