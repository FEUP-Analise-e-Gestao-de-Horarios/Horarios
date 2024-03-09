from django.db import models
from users.models import CustomUser
from django.utils import timezone

# Person atributes
class Person(models.Model):
    username = models.ForeignKey(CustomUser, db_column="user", on_delete=models.CASCADE)
    groups = models.ManyToManyField("Group", blank=True)

    def __str__(self):
        return f"{self.username}"

# Group atributes
class Group(models.Model):
    abreviation = models.TextField(unique=True)
    name = models.TextField()

    def __str__(self):
        return f"{self.abreviation}, {self.name}"

# Project atributes
class Project(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    project = models.TextField(unique=True)
    group = models.ManyToManyField("Group", blank=True)
    people = models.ManyToManyField("Person", related_name="People", blank=True)
    isParsed = models.BooleanField(default=False)
    data = models.DateField(default=timezone.now)
    
    def __str__(self):
        return f"{self.project}, {self.person}, {self.group}"
    
