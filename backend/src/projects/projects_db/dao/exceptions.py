from collections.abc import Collection


class MultipleNotFoundError(Exception):
    """Raised when a bulk lookup fails to find all requested records.

    Args:
        attribute: The field name used for the lookup (e.g. ``"number"``).
        missing_values: The values for which no record was found.
    """

    def __init__(self, attribute: str, missing_values: Collection[object]) -> None:
        super().__init__(
            f"Could not find {len(missing_values)} records with '{attribute}' in: {list(missing_values)}",
        )
