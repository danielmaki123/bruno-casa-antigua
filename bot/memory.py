import logging
from datetime import datetime, timedelta

from database.postgres import execute_query

logger = logging.getLogger(__name__)


def save(
    chat_id: int,
    user_id: int | None,
    user_name: str | None,
    role: str,
    content: str,
) -> None:
    try:
        execute_query(
            """
            INSERT INTO conversations (chat_id, user_id, user_name, role, content)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (chat_id, user_id, user_name, role, content),
        )
    except Exception as e:
        logger.error(f"memory.save error: {e}")


def get_context(chat_id: int, limit: int = 10) -> list[dict]:
    try:
        rows = execute_query(
            """
            SELECT role, content, created_at
            FROM conversations
            WHERE chat_id = %s
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (chat_id, limit),
            fetch=True,
        )
        return list(reversed([dict(r) for r in (rows or [])]))
    except Exception as e:
        logger.error(f"memory.get_context error: {e}")
        return []


def cleanup(days: int = 30) -> None:
    cutoff = datetime.utcnow() - timedelta(days=days)
    try:
        execute_query(
            "DELETE FROM conversations WHERE created_at < %s",
            (cutoff,),
        )
        logger.info(f"memory.cleanup: conversaciones anteriores a {cutoff.date()} eliminadas")
    except Exception as e:
        logger.error(f"memory.cleanup error: {e}")


def get_recent(chat_id: int, limit: int = 5) -> list[dict]:
    try:
        rows = execute_query(
            """
            SELECT role, content, timestamp
            FROM conversation_memory
            WHERE chat_id = %s
            ORDER BY timestamp DESC
            LIMIT %s
            """,
            (chat_id, limit),
            fetch=True,
        )
        return list(reversed([{"role": r["role"], "content": r["content"]} for r in (rows or [])]))
    except Exception as e:
        logger.error(f"memory.get_recent error: {e}")
        return []
