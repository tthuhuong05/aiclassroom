import random
import string


def generate_code(length=6):
    """
    Generate a random code for password reset or verification.
    
    Args:
        length (int): Length of the code. Default is 6.
    
    Returns:
        str: A random code consisting of uppercase letters and digits.
    """
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

