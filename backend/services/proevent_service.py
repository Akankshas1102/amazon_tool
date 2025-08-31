from sqlalchemy import text
from config import get_db_connection
from logger import get_logger
from config import execute_query

logger = get_logger(__name__)

def set_proevent_reactive(proevent_id: int, reactive: int):
    sql = text("""
        UPDATE ProEvent_TBL
        SET pevReactive_FRK = :reactive
        WHERE pevProEvent_PK = :proevent_id
    """)
    with get_db_connection() as conn:
        result = conn.execute(sql, {"reactive": reactive, "proevent_id": proevent_id})
        conn.commit()
        return result.rowcount
