"""Shared test setup.

Environment defaults are set before any test imports `agentcare.main`,
which builds the app at import time and needs `SECRET_KEY`.
"""

import os

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("APP_ENV", "test")
