import argparse

from sqlalchemy.orm import Session

from app.models.user import User
from app.services.auth import create_user, hash_password
from db import SessionLocal


def upsert_user(
    email: str, first: str, last: str, password: str | None, make_admin: bool, verify_email: bool
) -> tuple[bool, int]:
    s: Session = SessionLocal()
    try:
        user = s.query(User).filter(User.Email == email).first()
        created = False
        if not user:
            if not password:
                raise ValueError("Password required to create a new user")
            user = create_user(s, first, last, email, password)
            if not user:
                raise ValueError("Email already exists or failed to create user")
            created = True
        else:
            # Update names if provided
            if first:
                setattr(user, "FirstName", first)
            if last:
                setattr(user, "LastName", last)
            if password:
                setattr(user, "HashedPassword", hash_password(password))
        # Flags
        if verify_email:
            setattr(user, "EmailVerified", True)
        setattr(user, "IsActive", True)
        if make_admin:
            setattr(user, "IsAdmin", True)
        s.commit()
        s.refresh(user)
        return created, int(getattr(user, "UserID"))
    finally:
        s.close()


def main():
    parser = argparse.ArgumentParser(description="Create or update a user (optionally admin).")
    parser.add_argument("--email", required=True)
    parser.add_argument("--first", default="")
    parser.add_argument("--last", default="")
    parser.add_argument("--password", default=None)
    parser.add_argument("--admin", action="store_true", help="Grant admin role")
    parser.add_argument("--verify", action="store_true", help="Mark email as verified")
    args = parser.parse_args()

    created, user_id = upsert_user(
        email=args.email.strip(),
        first=args.first.strip(),
        last=args.last.strip(),
        password=args.password,
        make_admin=bool(args.admin),
        verify_email=bool(args.verify),
    )
    status = "created" if created else "updated"
    print(
        f"User {status}: id={user_id} email={args.email} admin={args.admin} verified={args.verify}"
    )


if __name__ == "__main__":
    main()
