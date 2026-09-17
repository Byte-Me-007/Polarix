import maitri.models  # noqa: F401 - Register models with Base.metadata
from maitri.database import Base, engine


def init_db():
    Base.metadata.create_all(bind=engine)
