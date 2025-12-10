#!/usr/bin/env python
"""Test password truncation for bcrypt 72-byte limit."""

import sys
sys.path.insert(0, '.')

from app.services.auth import hash_password, verify_password

# Test 1: Short password (should work fine)
short_pwd = 'T3qu1la!?!'
print(f'\n=== Test 1: Short password ===')
print(f'Password: {short_pwd}')
print(f'Length: {len(short_pwd)} chars, {len(short_pwd.encode("utf-8"))} bytes')
try:
    hashed = hash_password(short_pwd)
    print(f'✓ Hash succeeded')
    if verify_password(short_pwd, hashed):
        print(f'✓ Verification succeeded')
    else:
        print(f'✗ Verification failed')
except Exception as e:
    print(f'✗ Error: {e}')

# Test 2: Very long password (> 72 bytes)
long_pwd = 'T3qu1la!?!' * 20
print(f'\n=== Test 2: Long password ===')
print(f'Length: {len(long_pwd)} chars, {len(long_pwd.encode("utf-8"))} bytes')
try:
    hashed = hash_password(long_pwd)
    print(f'✓ Hash succeeded (truncated to 72 bytes)')
    if verify_password(long_pwd, hashed):
        print(f'✓ Verification succeeded with original long password')
    else:
        print(f'✗ Verification failed')
except Exception as e:
    print(f'✗ Error: {e}')

# Test 3: Unicode password (multi-byte chars)
unicode_pwd = '日本語パスワード!@#$'
print(f'\n=== Test 3: Unicode password ===')
print(f'Password: {unicode_pwd}')
print(f'Length: {len(unicode_pwd)} chars, {len(unicode_pwd.encode("utf-8"))} bytes')
try:
    hashed = hash_password(unicode_pwd)
    print(f'✓ Hash succeeded')
    if verify_password(unicode_pwd, hashed):
        print(f'✓ Verification succeeded')
    else:
        print(f'✗ Verification failed')
except Exception as e:
    print(f'✗ Error: {e}')

print('\n=== All tests completed ===')
