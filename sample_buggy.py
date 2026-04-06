"""
sample_buggy.py — Intentionally flawed code for testing CodeSentinel.
Contains: SQL injection, division by zero, missing error handling, poor naming, etc.
"""

import sqlite3
import os


DB_PATH = "users.db"


def get_user(username):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # BUG: SQL injection vulnerability
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    return cursor.fetchone()
    # BUG: connection never closed


def calculate_average(numbers):
    # BUG: division by zero if list is empty
    total = 0
    for n in numbers:
        total += n
    return total / len(numbers)


def read_file(path):
    # BUG: path traversal vulnerability, no validation
    full_path = os.path.join("/var/data/", path)
    f = open(full_path, "r")
    data = f.read()
    # BUG: file never closed
    return data


def process(x, y, z):  # BAD: meaningless name, too many responsibilities
    # Magic numbers, no docstring
    result = x * 1.08
    if result > 10000:
        result = result * 0.95
    d = result / (y - z)   # BUG: division by zero if y == z
    return d


password = "supersecret123"   # BUG: hardcoded secret
API_KEY = "sk-abc123xyz"      # BUG: hardcoded API key


class u:   # BAD: terrible class name
    def __init__(self, n, a, e):   # BAD: single-letter params
        self.n = n
        self.a = a
        self.e = e

    def get_info(self):
        return f"{self.n} ({self.a}) - {self.e}"