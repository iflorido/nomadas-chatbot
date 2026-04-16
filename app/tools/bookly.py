"""
bookly.py — Consultas de solo lectura a la BD de WordPress/Bookly Pro
Prefijo de tablas: w6H3p_ (configurable via DB_PREFIX en .env)
capacity_max viene de w6H3p_bookly_services
"""

import os
from datetime import datetime, date, timedelta
from typing import Optional
import aiomysql
from dotenv import load_dotenv

load_dotenv()

PREFIX = os.getenv("DB_PREFIX", "w6H3p_")

_pool: Optional[aiomysql.Pool] = None

DAYS = {1: "Lunes", 2: "Martes", 3: "Miércoles", 4: "Jueves",
        5: "Viernes", 6: "Sábado", 7: "Domingo"}


async def get_pool() -> aiomysql.Pool:
    global _pool
    if _pool is None:
        _pool = await aiomysql.create_pool(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", 3306)),
            db=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            autocommit=True,
            minsize=1,
            maxsize=5,
        )
    return _pool


async def close_pool():
    global _pool
    if _pool:
        _pool.close()
        await _pool.wait_closed()
        _pool = None


async def fetchall(sql: str, args=()) -> list[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(sql, args)
            return await cur.fetchall()


async def fetchone(sql: str, args=()) -> Optional[dict]:
    rows = await fetchall(sql, args)
    return rows[0] if rows else None


# ── Servicios ──────────────────────────────────────────────────────────────

async def get_services() -> list[dict]:
    sql = f"""
        SELECT id, title, duration AS duracion_minutos,
               price AS precio, capacity_max AS aforo_maximo, info
        FROM {PREFIX}bookly_services
        ORDER BY title
    """
    return await fetchall(sql)


async def get_service_by_id(service_id: int) -> Optional[dict]:
    sql = f"""
        SELECT id, title, duration AS duracion_minutos,
               price AS precio, capacity_max AS aforo_maximo, info
        FROM {PREFIX}bookly_services WHERE id = %s
    """
    return await fetchone(sql, (service_id,))


# ── Staff ──────────────────────────────────────────────────────────────────

async def get_staff() -> list[dict]:
    sql = f"""
        SELECT s.id, s.full_name,
               GROUP_CONCAT(srv.title ORDER BY srv.title SEPARATOR ', ') AS servicios
        FROM {PREFIX}bookly_staff s
        JOIN {PREFIX}bookly_staff_services ss ON ss.staff_id = s.id
        JOIN {PREFIX}bookly_services srv ON srv.id = ss.service_id
        GROUP BY s.id ORDER BY s.full_name
    """
    return await fetchall(sql)


async def get_staff_for_service(service_id: int) -> list[dict]:
    sql = f"""
        SELECT s.id, s.full_name
        FROM {PREFIX}bookly_staff s
        JOIN {PREFIX}bookly_staff_services ss ON ss.staff_id = s.id
        WHERE ss.service_id = %s
    """
    return await fetchall(sql, (service_id,))


# ── Horarios ───────────────────────────────────────────────────────────────

async def get_schedule(staff_id: Optional[int] = None) -> list[dict]:
    if staff_id:
        sql = f"""
            SELECT si.staff_id, s.full_name, si.day_of_week,
                   si.start_time, si.end_time
            FROM {PREFIX}bookly_staff_schedule_items si
            JOIN {PREFIX}bookly_staff s ON s.id = si.staff_id
            WHERE si.staff_id = %s ORDER BY si.day_of_week
        """
        rows = await fetchall(sql, (staff_id,))
    else:
        sql = f"""
            SELECT si.staff_id, s.full_name, si.day_of_week,
                   si.start_time, si.end_time
            FROM {PREFIX}bookly_staff_schedule_items si
            JOIN {PREFIX}bookly_staff s ON s.id = si.staff_id
            ORDER BY si.staff_id, si.day_of_week
        """
        rows = await fetchall(sql)

    for row in rows:
        row["dia"] = DAYS.get(row["day_of_week"], "?")
        row["abierto"] = row["start_time"] is not None
        for field in ("start_time", "end_time"):
            val = row.get(field)
            if isinstance(val, timedelta):
                total = int(val.total_seconds())
                h, m = divmod(total // 60, 60)
                row[field] = f"{h:02d}:{m:02d}"
    return rows


# ── Disponibilidad ─────────────────────────────────────────────────────────

async def get_available_slots(
    service_id: Optional[int] = None,
    desde: Optional[date] = None,
    hasta: Optional[date] = None,
) -> list[dict]:
    """
    Appointments con plazas libres.
    capacity_max viene de w6H3p_bookly_services (confirmado).
    """
    if desde is None:
        desde = date.today()
    if hasta is None:
        hasta = desde + timedelta(days=30)

    if service_id:
        service_clause = "AND a.service_id = %s"
        args = (desde, hasta, service_id)
    else:
        service_clause = ""
        args = (desde, hasta)

    sql = f"""
        SELECT
            a.id                                  AS appointment_id,
            srv.title                             AS servicio,
            a.service_id,
            st.full_name                          AS monitor,
            a.staff_id,
            a.start_date,
            a.end_date,
            COUNT(ca.id)                          AS plazas_ocupadas,
            srv.capacity_max                      AS aforo_maximo,
            (srv.capacity_max - COUNT(ca.id))     AS plazas_libres
        FROM {PREFIX}bookly_appointments a
        JOIN  {PREFIX}bookly_services  srv ON srv.id = a.service_id
        JOIN  {PREFIX}bookly_staff     st  ON st.id  = a.staff_id
        LEFT JOIN {PREFIX}bookly_customer_appointments ca ON ca.appointment_id = a.id
        WHERE a.start_date BETWEEN %s AND %s
        {service_clause}
        GROUP BY a.id, srv.capacity_max
        HAVING plazas_libres > 0
        ORDER BY a.start_date
    """
    rows = await fetchall(sql, args)

    for row in rows:
        if isinstance(row["start_date"], datetime):
            row["fecha"]      = row["start_date"].strftime("%d/%m/%Y")
            row["hora"]       = row["start_date"].strftime("%H:%M")
            row["dia_semana"] = DAYS.get(row["start_date"].isoweekday(), "")
        row["start_date"] = str(row["start_date"])
        row["end_date"]   = str(row["end_date"])

    return rows


async def get_slots_by_service_name(service_name: str) -> list[dict]:
    services = await get_services()
    matched = [s for s in services if service_name.upper() in s["title"].upper()]
    if not matched:
        return []
    return await get_available_slots(service_id=matched[0]["id"])


# ── Resumen inicial ────────────────────────────────────────────────────────

async def get_summary() -> dict:
    services = await get_services()
    staff    = await get_staff()
    slots    = await get_available_slots()
    return {
        "servicios": services,
        "monitores": staff,
        "proximas_plazas_disponibles": slots[:10],
    }
