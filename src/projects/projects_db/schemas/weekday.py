from enum import StrEnum


class WeekDay(StrEnum):
    """Days of the week, with Portuguese values for compatibility with external services."""

    MONDAY = "Segunda"
    TUESDAY = "Terça"
    WEDNESDAY = "Quarta"
    THURSDAY = "Quinta"
    FRIDAY = "Sexta"
    SATURDAY = "Sábado"

    @classmethod
    def _missing_(cls, value: object) -> WeekDay:
        """Look up a ``WeekDay`` by a case-insensitive English or Portuguese name."""
        if not isinstance(value, str):
            raise ValueError(f"{value!r} is not a valid WeekDay")

        normalized = value.strip().lower()
        aliases: dict[str, WeekDay] = {
            "monday": cls.MONDAY,
            "segunda": cls.MONDAY,
            "tuesday": cls.TUESDAY,
            "terça": cls.TUESDAY,
            "terca": cls.TUESDAY,
            "wednesday": cls.WEDNESDAY,
            "quarta": cls.WEDNESDAY,
            "thursday": cls.THURSDAY,
            "quinta": cls.THURSDAY,
            "friday": cls.FRIDAY,
            "sexta": cls.FRIDAY,
            "saturday": cls.SATURDAY,
            "sábado": cls.SATURDAY,
            "sabado": cls.SATURDAY,
        }

        if normalized not in aliases:
            raise ValueError(f"{value!r} is not a valid WeekDay")

        return aliases[normalized]
