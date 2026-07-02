"""Pure-logic smoke test: no database, no Django settings for models."""

from src.projects.projects_db.dao.parallel_candidate_graph import build_candidate_components


def test_build_candidate_components_empty() -> None:
    """With no slot rows there are no candidate components."""
    assert build_candidate_components([]) == []
