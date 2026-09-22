import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def client(tmp_path, monkeypatch):
    """A TestClient backed by a throwaway SQLite DB and upload dir."""
    from app.core import database

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    import app.models  # noqa: F401  (register models)
    database.Base.metadata.create_all(bind=engine)

    from app.core.config import settings
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path / "uploads"))

    from app.main import app

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[database.get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def sample_df():
    rng = np.random.default_rng(42)
    n = 160
    activity = np.where(rng.random(n) < 0.5, "Active", "Inactive")
    sbp = rng.normal(120, 10, n) + (activity == "Inactive") * 7
    return pd.DataFrame(
        {
            "student_id": [f"S{i:03d}" for i in range(n)],
            "activity_level": activity,
            "systolic_bp": sbp.round(1),
            "diastolic_bp": (rng.normal(78, 8, n) + (activity == "Inactive") * 4).round(1),
            "bmi": (22 + 0.05 * sbp + rng.normal(0, 2, n)).round(1),
            "age": rng.integers(18, 30, n),
            "sex": rng.choice(["M", "F"], n),
            "year_group": rng.choice(["Year 1", "Year 2", "Year 3"], n),
        }
    )
