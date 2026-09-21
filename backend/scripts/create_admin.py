import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.models  # noqa: F401
from sqlalchemy import select

from app.core.database import Base, SessionLocal, engine
from app.models.user import User
from app.services.auth_service import hash_password


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == "admin@example.com"))
        if user is None:
            user = User(
                email="admin@example.com",
                full_name="Platform Admin",
                hashed_password=hash_password("admin123"),
                is_superuser=True,
            )
            db.add(user)
            db.commit()
            print("Created admin@example.com")
        else:
            user.is_superuser = True
            db.commit()
            print("Admin already exists; ensured superuser access")
    finally:
        db.close()


if __name__ == "__main__":
    main()
