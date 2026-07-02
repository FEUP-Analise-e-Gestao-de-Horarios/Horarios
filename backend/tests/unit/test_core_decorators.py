"""Unit tests for :mod:`src.core.decorators`.

``require_auth`` is pure (it only reads ``request.user.is_authenticated``), so
it is exercised with lightweight ``SimpleNamespace`` stand-ins for the view,
request and user. ``require_project`` queries the Django ORM for a matching
``Project``, so those cases depend on the ``db``/``project`` fixtures. This file
owns the decorator *unit* tests; the end-to-end "401 beats 404" ordering through
the HTTP client lives in the integration suite.
"""

import json
from types import SimpleNamespace

import pytest

from src.core.decorators import require_auth, require_project

SENTINEL = object()


def _request(*, is_authenticated: bool) -> SimpleNamespace:
    """A minimal stand-in for an ``HttpRequest`` with the needed ``user`` attr."""
    return SimpleNamespace(user=SimpleNamespace(is_authenticated=is_authenticated))


class _View:
    """A view whose method records whether it ran and echoes its arguments."""

    def __init__(self) -> None:
        self.called = False
        self.received: tuple[object, ...] | None = None
        self.received_kwargs: dict[str, object] | None = None

    @require_auth
    def guarded_by_auth(self, request, *args, **kwargs):
        self.called = True
        self.received = args
        self.received_kwargs = kwargs
        return SENTINEL

    @require_project
    def guarded_by_project(self, request, *args, **kwargs):
        self.called = True
        self.received = args
        self.received_kwargs = kwargs
        return SENTINEL


def _body(response) -> dict[str, object]:
    """Decode the JSON body of a ``JsonResponse``."""
    return json.loads(response.content)


# --------------------------------------------------------------------------- #
# require_auth
# --------------------------------------------------------------------------- #


def test_require_auth_passes_through_when_authenticated() -> None:
    """An authenticated request runs the wrapped method and returns its result."""
    view = _View()

    result = view.guarded_by_auth(_request(is_authenticated=True))

    assert result is SENTINEL
    assert view.called is True


def test_require_auth_returns_401_and_skips_method_when_unauthenticated() -> None:
    """An unauthenticated request short-circuits to a 401 without running the method."""
    view = _View()

    response = view.guarded_by_auth(_request(is_authenticated=False))

    assert view.called is False
    assert response.status_code == 401
    assert _body(response) == {
        "error": "auth.not_authenticated",
        "message": "User is not authenticated.",
    }


def test_require_auth_forwards_args_and_kwargs() -> None:
    """Positional and keyword arguments are forwarded to the wrapped method verbatim."""
    view = _View()

    result = view.guarded_by_auth(_request(is_authenticated=True), 7, extra="z")

    assert result is SENTINEL
    assert view.received == (7,)
    assert view.received_kwargs == {"extra": "z"}


def test_require_auth_preserves_metadata_via_wraps() -> None:
    """``functools.wraps`` keeps the wrapped method's ``__name__``."""
    assert _View.guarded_by_auth.__name__ == "guarded_by_auth"


# --------------------------------------------------------------------------- #
# require_project
# --------------------------------------------------------------------------- #


def test_require_project_passes_through_when_project_exists(project) -> None:
    """A ``project_id`` matching an existing project runs the wrapped method."""
    view = _View()

    result = view.guarded_by_project(_request(is_authenticated=True), project_id=project.pk)

    assert result is SENTINEL
    assert view.called is True


def test_require_project_returns_404_and_skips_method_when_missing(db) -> None:
    """An unknown ``project_id`` short-circuits to a 404 without running the method."""
    view = _View()

    response = view.guarded_by_project(_request(is_authenticated=True), project_id=999999)

    assert view.called is False
    assert response.status_code == 404
    assert _body(response) == {
        "error": "projects.not_found",
        "message": "Project not found.",
    }


def test_require_project_404_uses_a_definitely_absent_pk(project) -> None:
    """A pk far past the real project's is treated as absent and yields a 404."""
    view = _View()

    response = view.guarded_by_project(
        _request(is_authenticated=True),
        project_id=project.pk + 1000,
    )

    assert view.called is False
    assert response.status_code == 404


def test_require_project_raises_keyerror_when_project_id_absent(db) -> None:
    """``require_project`` reads ``kwargs['project_id']`` directly; omitting it raises."""
    view = _View()

    with pytest.raises(KeyError) as excinfo:
        view.guarded_by_project(_request(is_authenticated=True))

    assert excinfo.value.args == ("project_id",)


def test_require_project_forwards_args_and_kwargs(project) -> None:
    """Extra positional/keyword args are forwarded past the project guard verbatim."""
    view = _View()

    result = view.guarded_by_project(
        _request(is_authenticated=True),
        7,
        project_id=project.pk,
        extra="z",
    )

    assert result is SENTINEL
    assert view.received == (7,)
    assert view.received_kwargs == {"project_id": project.pk, "extra": "z"}


def test_require_project_preserves_metadata_via_wraps() -> None:
    """``functools.wraps`` keeps the wrapped method's ``__name__``."""
    assert _View.guarded_by_project.__name__ == "guarded_by_project"
