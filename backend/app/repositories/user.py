"""User repository (PostgreSQL async).

Contains only database operations. Business logic (password hashing,
validation) is handled by UserService in app/services/user.py.
"""

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User


async def get_by_id(db: AsyncSession, user_id: UUID) -> User | None:
    """Get user by ID."""
    return await db.get(User, user_id)


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    """Get user by email."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_by_oauth(db: AsyncSession, provider: str, oauth_id: str) -> User | None:
    """Get user by OAuth provider and ID."""
    result = await db.execute(
        select(User).where(User.oauth_provider == provider, User.oauth_id == oauth_id)
    )
    return result.scalar_one_or_none()


async def get_multi(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 100,
) -> list[User]:
    """Get multiple users with pagination."""
    result = await db.execute(select(User).offset(skip).limit(limit))
    return list(result.scalars().all())


async def create(
    db: AsyncSession,
    *,
    email: str,
    hashed_password: str | None,
    full_name: str | None = None,
    is_active: bool = True,
    role: str = "user",
    oauth_provider: str | None = None,
    oauth_id: str | None = None,
) -> User:
    """Create a new user.

    Note: Password should already be hashed by the service layer.
    """
    user = User(
        email=email,
        hashed_password=hashed_password,
        full_name=full_name,
        is_active=is_active,
        role=role,
        oauth_provider=oauth_provider,
        oauth_id=oauth_id,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def update(
    db: AsyncSession,
    *,
    db_user: User,
    update_data: dict[str, Any],
) -> User:
    """Update a user.

    Note: If password needs updating, it should already be hashed.
    """
    for field, value in update_data.items():
        setattr(db_user, field, value)

    db.add(db_user)
    await db.flush()
    await db.refresh(db_user)
    return db_user


async def update_avatar(db: AsyncSession, user_id: UUID, avatar_url: str) -> User:
    """Update a user's avatar URL."""
    user = await db.get(User, user_id)
    if user is None:
        raise ValueError(f"User {user_id} not found")
    user.avatar_url = avatar_url
    await db.flush()
    await db.refresh(user)
    return user


async def delete(db: AsyncSession, user_id: UUID) -> User | None:
    """Delete a user."""
    user = await get_by_id(db, user_id)
    if user:
        await db.delete(user)
        await db.flush()
    return user
