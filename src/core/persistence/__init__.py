"""No-op persistence stub.

The full persistence/DB layer was removed during cleanup.
This stub prevents ImportError in modules that reference db_manager.
"""


class _NoOpDbManager:
    """All calls silently succeed and return safe defaults."""

    def __getattr__(self, name):
        return lambda *a, **kw: None

    def get_generation_history(self, **kw):
        return []

    def get_generation_record(self, job_id):
        return None

    def get_config_history(self, **kw):
        return []


db_manager = _NoOpDbManager()
backup_manager = _NoOpDbManager()
