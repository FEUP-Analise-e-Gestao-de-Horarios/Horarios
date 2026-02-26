from django.contrib import admin

from core.models import Person, Group, Project

@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ("username", )
    list_filter = ("groups", )
    search_fields = ("username__startswith", )

@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    search_fields = ("abreviation__startswith", )

@admin.register(Project)
class GradeAdmin(admin.ModelAdmin):
    search_fields = ("project__startswith", )
    list_display = ("project", )
    list_filter = ("person", "group", )
