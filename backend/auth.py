"""
ThyroScan — Authentication & Session Management
Provides password hashing (PBKDF2 SHA256), JWT tokens, and route protection.
"""

import os
import hashlib
import secrets
import jwt
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import request, jsonify
from backend.database import get_db

SECRET_KEY = os.environ.get('SECRET_KEY', 'thyroscan-ai-screening-secret-key-2026')
JWT_ALGORITHM = 'HS256'
TOKEN_EXPIRY_DAYS = 7


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    ).hex()
    return f"{salt}${pwd_hash}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, pwd_hash = stored_hash.split('$')
        check_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        ).hex()
        return secrets.compare_digest(pwd_hash, check_hash)
    except Exception:
        return False


def generate_token(user_id: int, email: str, name: str) -> str:
    payload = {
        'user_id': user_id,
        'email': email,
        'name': name,
        'exp': datetime.now(timezone.utc) + timedelta(days=TOKEN_EXPIRY_DAYS),
        'iat': datetime.now(timezone.utc)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def get_current_user():
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None
    token = auth_header.split(' ')[1]
    return decode_token(token)


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required. Please sign in.'}), 401
        return f(user, *args, **kwargs)
    return decorated
