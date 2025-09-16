# scripts/create_test_users.py
"""
Script to create test users for each package/plan: free, basic, ultimate.
Run this with your app's environment and DB configured.
"""

import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from passlib.hash import bcrypt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.user import User

# Load .env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

DB_SERVER = os.getenv('DB_SERVER')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_DRIVER = os.getenv('DB_DRIVER')
# Load .env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

DB_SERVER = os.getenv('DB_SERVER')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_DRIVER = os.getenv('DB_DRIVER')

# normalize driver string and keep the line length reasonable for linters
driver = DB_DRIVER.replace(' ', '+') if DB_DRIVER else ''
DATABASE_URL = f"mssql+pyodbc://{DB_USER}:{DB_PASSWORD}@{DB_SERVER}/{DB_NAME}?driver={driver}"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()


def create_user(email, password, plan):
    user = User(
        FirstName=plan.capitalize(),
        LastName="Test",
        Email=email,
        HashedPassword=bcrypt.hash(password),
        IsActive=True,
        EmailVerified=True,
    DateCreated=datetime.now(timezone.utc),
        plan=plan,
    plan_purchase_date=datetime.now(timezone.utc) if plan != "free" else None,
    )
    session.add(user)
    session.commit()
    print(f"Created user: {email} (plan: {plan})")


if __name__ == "__main__":
    print(f"Using DATABASE_URL: {DATABASE_URL}")
    try:
        # Create test users
        create_user("freeuser@example.com", "testpass123", "free")
        create_user("basicuser@example.com", "testpass123", "basic")
        create_user("ultimateuser@example.com", "testpass123", "ultimate")
        print("Test users created.")
    except Exception as e:
        print(f"Error creating users: {e}")
        import traceback
        traceback.print_exc()
