"""Shared test fixtures for Copa tests."""

import pytest
from pathlib import Path
from copa.db import Database


@pytest.fixture
def tmp_db(tmp_path):
    """Create an initialized temporary Copa database."""
    db_path = tmp_path / "test.db"
    db = Database(db_path)
    db.init_db()
    yield db
    db.close()


@pytest.fixture
def tmp_script(tmp_path):
    """Create a factory for temporary script files."""
    def _make_script(name: str, content: str) -> Path:
        script = tmp_path / name
        script.write_text(content)
        script.chmod(0o755)
        return script
    return _make_script
