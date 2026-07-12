from .auth import router as auth
from .pipeline import router as pipelines
from .admin import router as admin

__all__ = ['auth', 'pipelines', 'admin']
