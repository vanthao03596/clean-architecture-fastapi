"""Repository interfaces - define contracts for data access."""

from app.domain.repositories.base import IRepository
from app.domain.repositories.unit_of_work import IUnitOfWork
from app.domain.repositories.user_repository import IUserRepository

__all__ = ["IRepository", "IUserRepository", "IUnitOfWork"]
