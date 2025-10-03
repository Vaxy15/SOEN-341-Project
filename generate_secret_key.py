#!/usr/bin/env python3
"""
Generate a secure Django secret key.
Run this script to generate a new secret key for production.
"""

import secrets
import string

def generate_secret_key():
    """Generate a secure Django secret key."""
    # Use Django's default character set for secret keys
    chars = string.ascii_letters + string.digits + '!@#$%^&*(-_=+)'
    return ''.join(secrets.choice(chars) for _ in range(50))

if __name__ == '__main__':
    print("Generated Django Secret Key:")
    print(generate_secret_key())
    print("\nCopy this key to your .env file as SECRET_KEY=...")
