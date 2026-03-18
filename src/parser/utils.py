from django.http import HttpResponse
from pydantic import BaseModel, ValidationError


# TODO return user friendly errors
def validate_request_body[M: BaseModel](
    model: type[M],
    body: bytes,
) -> tuple[M, None] | tuple[None, HttpResponse]:
    try:
        return model.model_validate_json(body), None
    except ValidationError as e:
        return None, HttpResponse(
            e.json(),
            content_type="application/json",
            status=400,
        )
