import maitri.models  # noqa: F401 - Register models with Base.metadata
from maitri.database import Base, SessionLocal, engine
from maitri.services.resource_service import seed_default_resources
from maitri.services.station_service import seed_default_stations


from sqlalchemy import text

def init_db():
    Base.metadata.create_all(bind=engine)
    # Ensure any new columns exist on existing databases
    with engine.connect() as conn:
        for col_name in ("asset_id", "zone"):
            try:
                conn.execute(text(f"ALTER TABLE sensors ADD COLUMN {col_name} VARCHAR;"))
                conn.commit()
            except Exception:
                pass

    db = SessionLocal()
    try:
        seed_default_stations(db)
        seed_default_resources(db)
    finally:
        db.close()

