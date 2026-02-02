"""Tests de base pour Lele."""

import re


def test_version_format():
    """Vérifie que la version suit le format semver."""
    from lele import __version__

    # Format semver: MAJOR.MINOR.PATCH
    pattern = r"^\d+\.\d+\.\d+(-[\w.]+)?(\+[\w.]+)?$"
    assert re.match(pattern, __version__), f"Version '{__version__}' ne suit pas le format semver"


def test_version_exists():
    """Vérifie que la version est définie."""
    from lele import __version__

    assert __version__ is not None
    assert len(__version__) > 0


def test_author_exists():
    """Vérifie que l'auteur est défini."""
    from lele import __author__

    assert __author__ is not None
    assert len(__author__) > 0
