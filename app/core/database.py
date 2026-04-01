"""Legacy compatibility module.

The backend no longer uses a relational database. All persistence now happens
via files under the storage directory.
"""

engine = None
SessionLocal = None
Base = object


def get_db():
    raise RuntimeError(
        "Database sessions are no longer available. Use file-based storage services instead."
    )
