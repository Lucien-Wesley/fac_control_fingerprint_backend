import re

EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}$")


def is_valid_email(email: str) -> bool:
    if not isinstance(email, str):
        return False
    return EMAIL_REGEX.match(email) is not None


def require_non_empty(value: str, field_name: str):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} is required and must be a non-empty string")
    return value.strip()
