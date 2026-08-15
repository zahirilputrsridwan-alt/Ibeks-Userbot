@@
 def is_chat_locked(chat_id: int) -> bool:
     """Kembalikan True bila chat memiliki status lock aktif."""
     conn = get_conn()
     row = conn.execute(
         "SELECT locked FROM chat_lock WHERE chat_id = ?",
         (chat_id,),
     ).fetchone()
     return bool(row and row["locked"])
+
+
+def list_locked_chats() -> list[int]:
+    """Kembalikan daftar chat_id yang saat ini memiliki locked = 1."""
+    conn = get_conn()
+    rows = conn.execute("SELECT chat_id FROM chat_lock WHERE locked = 1").fetchall()
+    return [int(row["chat_id"]) for row in rows]
