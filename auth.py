# src/auth.py

import os
import json
import bcrypt
from fastapi import HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer

# Path to your users JSON file
USERS_FILE = "users.json"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# ------------------ USER STORAGE ------------------

def load_users():
    """Load users from JSON file."""
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, "r") as f:
        return json.load(f)


def save_users(users):
    """Save users to JSON file."""
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)


def get_user_by_email(email: str):
    """Get a user by email."""
    users = load_users()
    for user in users:
        if user["email"] == email:
            return user
    return None


# ------------------ AUTH ------------------

def authenticate_user(email: str, password: str):
    """Verify email and password."""
    user = get_user_by_email(email)
    if not user:
        return None
    if bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        return user
    return None


# ------------------ TOKEN ------------------

from datetime import datetime, timedelta
import jwt

SECRET_KEY = os.environ.get("SECRET_KEY", "supersecretkey")  # replace with secure key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 day


def create_access_token(data: dict, expires_delta: int = ACCESS_TOKEN_EXPIRE_MINUTES):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_delta)
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token


# ------------------ ADMIN ------------------

def get_admin_user(token: str = Depends(oauth2_scheme)):
    """Verify that the token belongs to an admin."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = get_user_by_email(email)
        if not user or not user.get("is_admin", False):
            raise HTTPException(status_code=403, detail="Admin privileges required")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
