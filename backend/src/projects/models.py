from datetime import datetime

from django.db import models
from django.db.models import (
    BooleanField,
    DateTimeField,
    ForeignKey,
    ManyToManyField,
    TextField,
)
from django.db.models.expressions import Combinable

from src.users.models import User


class Group(models.Model):
    """A named group of users that can be assigned to projects."""

    # Data
    abbreviation: TextField[str | Combinable, str] = TextField(unique=True)
    name: TextField[str | Combinable, str] = TextField()

    # Relationships
    members: ManyToManyField[User, User] = ManyToManyField(
        User,
        blank=True,
        related_name="member_groups",
    )

    def __str__(self) -> str:
        return f"[{self.abbreviation}] {self.name}"


class Project(models.Model):
    """A schedule project that holds ingested timetable data in its own SQLite database."""

    # Data
    name: TextField[str | Combinable, str] = TextField(unique=True)
    url: TextField[str | Combinable, str] = TextField()
    has_selected_parallel_sessions: BooleanField[bool | Combinable, bool] = BooleanField(
        default=False,
    )

    # Timestamps
    created_at: DateTimeField[
        datetime | str | Combinable,
        datetime,
    ] = DateTimeField(auto_now_add=True)
    updated_at: DateTimeField[
        datetime | str | Combinable,
        datetime,
    ] = DateTimeField(auto_now=True)
    ingestion_started_at: DateTimeField[
        datetime | str | Combinable | None,
        datetime | None,
    ] = DateTimeField(
        null=True,
        blank=True,
    )
    ingestion_finished_at: DateTimeField[
        datetime | str | Combinable | None,
        datetime | None,
    ] = DateTimeField(
        null=True,
        blank=True,
    )
    ingestion_failed_at: DateTimeField[
        datetime | str | Combinable | None,
        datetime | None,
    ] = DateTimeField(
        null=True,
        blank=True,
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
        return f"Project({self.name}) by {self.creator}"
