"""Password hashing with bcrypt."""

import bcrypt

# bcrypt refuses longer passwords, so registration rejects them and login treats them as wrong.
MAX_PASSWORD_BYTES = 72


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    if len(plain.encode()) > MAX_PASSWORD_BYTES:
        return False
    return bcrypt.checkpw(plain.encode(), hashed.encode())
