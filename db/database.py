"""
Database connection layer.

FastAPI never talks to Postgres "directly" — it goes through a pool
that is created once at startup and closed once at shutdown.
"""

from typing import AsyncGenerator

import asyncpg

from core.config import settings

pool: asyncpg.Pool | None = None


async def init_pool() -> None:
    """Create the connection pool. Called once on app startup."""
    global pool
    pool = await asyncpg.create_pool(
        dsn=settings.database_url,
        min_size=2,
        max_size=10,
    )


async def close_pool() -> None:
    """Close the connection pool. Called once on app shutdown."""
    global pool
    if pool:
        await pool.close()
        pool = None


async def get_conn() -> AsyncGenerator[asyncpg.Connection, None]:
    """
    Dependency that hands a live connection from the pool to any
    endpoint that declares `conn=Depends(get_conn)`.
    """
    if pool is None:
        raise RuntimeError("Connection pool is not initialized.")

    async with pool.acquire() as connection:
        yield connection
