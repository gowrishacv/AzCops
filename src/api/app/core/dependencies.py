from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import CurrentUser, get_current_user

DbSession = Annotated[AsyncSession, Depends(get_db_session)]
AuthenticatedUser = Annotated[CurrentUser, Depends(get_current_user)]


async def get_tenant_id(user: AuthenticatedUser) -> str:
    """Extract tenant_id from the authenticated user."""
    return user.tenant_id


TenantId = Annotated[str, Depends(get_tenant_id)]
