from typing import Any, Self

from pydantic import BaseModel


class ValidateWithExtrasMixin:
    """Mixin that adds attribute-based validation with extra fields support."""

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if not issubclass(cls, BaseModel):
            raise TypeError(
                f"{cls.__name__} must inherit from pydantic.BaseModel to use ValidateWithExtrasMixin",
            )

    @classmethod
    def model_validate_with_extras(cls, obj: object, extras: dict[str, Any]) -> Self:
        """Validate any attribute-bearing object using this Pydantic model, merging in extra fields.

        Fields present in both the object and extras are overridden by extras.

        Args:
            obj: Any object whose attributes are used to populate the model fields.
            extras: Additional fields to merge with (and override) the object data.

        Returns:
            An instance of this Pydantic model with validated data.
        """
        if not issubclass(cls, BaseModel):
            # Will never happen because of the __init_subclass__ check above.
            raise TypeError("model_validate_with_extras called from invalid class")

        obj_data = {field: getattr(obj, field) for field in cls.model_fields if hasattr(obj, field)}
        return cls.model_validate(obj_data | extras)
