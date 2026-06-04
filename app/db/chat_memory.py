from app.db.connection import db_cursor

SUMMARY_TRIGGER_TURNS = 6
RECENT_TURNS = 3


def create_session(user_id: str = "local_user") -> int:
    with db_cursor() as cursor:
        cursor.execute("INSERT INTO chat_sessions (user_id) VALUES (?)", (user_id,))
        return int(cursor.lastrowid)


def get_or_create_session(session_id: int | None, user_id: str = "local_user") -> dict:
    if session_id:
        with db_cursor() as cursor:
            cursor.execute(
                "SELECT id, user_id, summary, message_count FROM chat_sessions WHERE id = ?",
                (session_id,),
            )
            row = cursor.fetchone()
            if row:
                return row

    new_session_id = create_session(user_id)
    return {
        "id": new_session_id,
        "user_id": user_id,
        "summary": None,
        "message_count": 0,
    }


def add_message(session_id: int, role: str, content: str) -> None:
    with db_cursor() as cursor:
        cursor.execute(
            "INSERT INTO chat_messages (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content),
        )
        cursor.execute(
            "UPDATE chat_sessions SET message_count = message_count + 1 WHERE id = ?",
            (session_id,),
        )


def get_recent_turns(session_id: int, limit: int = RECENT_TURNS) -> list[dict[str, str]]:
    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT role, content
            FROM chat_messages
            WHERE session_id = ? AND is_summarized = FALSE
            ORDER BY id DESC
            LIMIT ?
            """,
            (session_id, limit * 2),
        )
        rows = list(reversed(cursor.fetchall()))

    turns: list[dict[str, str]] = []
    pending_user: str | None = None
    for row in rows:
        if row["role"] == "user":
            pending_user = row["content"]
        elif row["role"] == "assistant" and pending_user is not None:
            turns.append({"user": pending_user, "assistant": row["content"]})
            pending_user = None

    return turns[-limit:]


def get_unsummarized_turn_count(session_id: int) -> int:
    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT COUNT(*) AS message_count
            FROM chat_messages
            WHERE session_id = ? AND is_summarized = FALSE
            """,
            (session_id,),
        )
        row = cursor.fetchone()
    return int(row["message_count"] // 2)


def get_turns_to_summarize(session_id: int, keep_recent_turns: int = RECENT_TURNS) -> list[dict]:
    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT id, role, content
            FROM chat_messages
            WHERE session_id = ? AND is_summarized = FALSE
            ORDER BY id ASC
            """,
            (session_id,),
        )
        rows = cursor.fetchall()

    summarize_message_count = max(len(rows) - keep_recent_turns * 2, 0)
    return rows[:summarize_message_count]


def update_summary(session_id: int, summary: str, summarized_message_ids: list[int]) -> None:
    with db_cursor() as cursor:
        cursor.execute(
            "UPDATE chat_sessions SET summary = ? WHERE id = ?",
            (summary, session_id),
        )
        if summarized_message_ids:
            placeholders = ",".join(["?"] * len(summarized_message_ids))
            cursor.execute(
                f"UPDATE chat_messages SET is_summarized = TRUE WHERE id IN ({placeholders})",
                tuple(summarized_message_ids),
            )


def maybe_summarize_session(session_id: int, summary: str | None, summarizer) -> str | None:
    if get_unsummarized_turn_count(session_id) <= SUMMARY_TRIGGER_TURNS:
        return summary

    rows = get_turns_to_summarize(session_id)
    if not rows:
        return summary

    new_summary = summarizer(summary or "", rows)
    update_summary(session_id, new_summary, [int(row["id"]) for row in rows])
    return new_summary
