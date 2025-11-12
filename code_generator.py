import secrets
import string

def generate_code(length: int = 6, alphabet: str = None) -> str:
    """
    Generate a secure random verification code.

    Args:
        length: number of characters in the code (default 6).
        alphabet: optional string of characters to use. If None, use digits.

    Returns:
        A random string of the requested length.
    """
    if alphabet is None:
        alphabet = string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


if __name__ == "__main__":
    print(generate_code())
