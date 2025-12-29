# sitecustomize.py (repo root)
import os
import sys

ROOT = os.path.dirname(__file__)

EXTRA_PATHS = [
    os.path.join(ROOT, "packages", "core", "src"),
    os.path.join(ROOT, "apps", "api", "src"),
    os.path.join(ROOT, "apps", "worker", "src"),
]

for p in EXTRA_PATHS:
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)
