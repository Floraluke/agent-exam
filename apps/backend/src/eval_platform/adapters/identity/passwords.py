from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from argon2.low_level import Type


class Argon2Passwords:
    def __init__(self) -> None:
        self._hasher = PasswordHasher(
            time_cost=3, memory_cost=65536, parallelism=4, type=Type.ID
        )

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, encoded: str, password: str) -> bool:
        try:
            return self._hasher.verify(encoded, password)
        except (InvalidHashError, VerificationError):
            return False
