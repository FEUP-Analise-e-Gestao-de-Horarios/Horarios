from datetime import date

from django.db import models
from django.db.models import (
    BooleanField,
    DateField,
    ForeignKey,
    ManyToManyField,
    TextField,
)
from django.db.models.expressions import Combinable
from django.utils import timezone

from src.users.models import User


class Group(models.Model):
    # Data
    abreviation: TextField[str | Combinable, str] = TextField(unique=True)
    name: TextField[str | Combinable, str] = TextField()

    # Relationships
    members: ManyToManyField[User, User] = ManyToManyField(
        User,
        blank=True,
        related_name="member_groups",
    )

    def __str__(self) -> str:
        return f"[{self.abreviation}] {self.name}"


class Project(models.Model):
    # Data
    project: TextField[str | Combinable, str] = TextField(unique=True)
    isParsed: BooleanField[bool | Combinable, bool] = BooleanField(default=False)
    data: DateField[str | date | Combinable, date] = DateField(default=timezone.now)
    has_selected_aulas_em_paralelo: BooleanField[bool | Combinable, bool] = (
        BooleanField(default=False)
    )

    # Relationships
    creator: ForeignKey[User | Combinable, User] = ForeignKey(
        User,
        on_delete=models.CASCADE,
    )
    group: ManyToManyField[Group, Group] = ManyToManyField(
        "Group",
        blank=True,
        related_name="project_groups",
    )
    people: ManyToManyField[User, User] = ManyToManyField(
        User,
        related_name="projects",
        blank=True,
    )

    def __str__(self) -> str:
        return f"Project({self.project}) by {self.creator}"
