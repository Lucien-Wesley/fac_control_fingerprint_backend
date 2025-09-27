from __future__ import annotations

import os
from faker import Faker

from app import app
from utils.db import db
from models import Student, Professor, User


def ensure_admin(fake: Faker) -> None:
    # Create an admin user if not exists
    admin = User.query.filter_by(username="admin").first()
    if admin:
        return
    admin = User(
        username="admin",
        email="admin@example.com",
        role="admin",
    )
    admin.set_password("Admin123!")
    db.session.add(admin)


def seed_students(fake: Faker, n: int = 5) -> None:
    for _ in range(n):
        name = fake.name()
        email = fake.unique.email()
        major = fake.random_element(elements=("CS", "Math", "Physics", "Biology", "Economics"))
        s = Student(name=name, email=email, major=major, fingerprint_verified=True)
        db.session.add(s)


def seed_professors(fake: Faker, n: int = 5) -> None:
    for _ in range(n):
        name = fake.name()
        email = fake.unique.email()
        dept = fake.random_element(elements=("CS", "Math", "Physics", "Biology", "Economics"))
        p = Professor(name=name, email=email, department=dept, fingerprint_verified=True)
        db.session.add(p)


def main():
    # Allow overriding count via env if needed
    count = int(os.getenv("SEED_COUNT", 5))
    fake = Faker()
    fake.seed_instance(12345)

    with app.app_context():
        # Create tables if not exist
        db.create_all()

        ensure_admin(fake)
        seed_students(fake, n=count)
        seed_professors(fake, n=count)

        db.session.commit()
        print(f"Seeded admin + {count} students + {count} professors.")


if __name__ == "__main__":
    main()
