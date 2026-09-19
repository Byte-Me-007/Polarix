import maitri.models  # noqa: F401 - Register models with Base.metadata
from maitri.database import Base, SessionLocal, engine
from maitri.services.resource_service import seed_default_resources
from maitri.services.station_service import seed_default_stations


def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_default_stations(db)
        seed_default_resources(db)
    finally:
        db.close()

