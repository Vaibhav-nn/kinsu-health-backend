"""Legacy compatibility shim for Vault router imports."""

from app.api.v1.vault import router

__all__ = ["router"]
