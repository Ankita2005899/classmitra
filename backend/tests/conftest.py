import os

# Tests use their own throw-away database, never your real MySQL.
os.environ["DATABASE_URL"] = "sqlite:///./test_classmitra.db"

import pytest  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _database():
    from app.db import Base, engine

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    engine.dispose()
    if os.path.exists("test_classmitra.db"):
        os.remove("test_classmitra.db")
