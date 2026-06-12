"""
Módulo: admin
=============
Endpoints de métricas para el Dashboard de gestión.
Consultan agregaciones sobre Pedido, DetallePedido y Producto.

Seguridad: solo ADMIN / GESTOR_STOCK / GESTOR_PEDIDOS.
"""
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel import Session, select, func

from core.database import get_session
from core.security import RoleChecker, get_current_user_token, TokenData
from app.modules.pedido.models import Pedido, DetallePedido
from app.modules.catalogo.producto.models import Producto

router = APIRouter(
    prefix="/admin/dashboard",
    tags=["Admin — Dashboard"],
    dependencies=[Depends(RoleChecker(["ADMIN", "GESTOR_STOCK", "GESTOR_PEDIDOS"]))],
)


# ── Schemas de respuesta ──────────────────────────────────────────────────
class ProductoVendidoOut(BaseModel):
    nombre: str
    cantidad: int


class IngresoMensualOut(BaseModel):
    mes: str
    ingreso: float
    anio: int


class RentabilidadOut(BaseModel):
    nombre: str
    margen: float        # porcentaje
    ganancia: float      # $ por unidad (precio - costo)


class KpisOut(BaseModel):
    total_ingresos: float
    total_pedidos: int
    promedio_por_pedido: float


class DashboardDataOut(BaseModel):
    total_ingresos: float
    total_pedidos: int
    promedio_por_pedido: float
    productos_mas_vendidos: List[ProductoVendidoOut]
    ingresos_mensuales: List[IngresoMensualOut]
    rentabilidad_por_producto: List[RentabilidadOut]


# ── Helpers ───────────────────────────────────────────────────────────────
MESES_ES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
            "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


def _rango_ultimos_meses(meses: int = 12) -> datetime:
    """Devuelve la fecha de hace N meses (inicio del mes) en UTC."""
    now = datetime.now(timezone.utc)
    # Ir al primer día del mes N meses atrás
    year = now.year
    month = now.month - meses
    while month <= 0:
        month += 12
        year -= 1
    return datetime(year, month, 1, tzinfo=timezone.utc)


# ── Endpoint agregado (1 sola llamada para todo el Dashboard) ─────────────
@router.get("", response_model=DashboardDataOut, summary="Datos completos del Dashboard")
def obtener_dashboard(
    session: Session = Depends(get_session),
    current_user: TokenData = Depends(get_current_user_token),
):
    """
    Devuelve KPIs + los 3 datasets para los gráficos en una sola respuesta.
    """
    # ── 1. KPIs globales ──
    kpi_row = session.exec(
        select(
            func.coalesce(func.sum(Pedido.total), 0).label("total_ingresos"),
            func.count(Pedido.id).label("total_pedidos"),
        ).where(Pedido.estado_codigo != "CANCELADO")
    ).one()
    total_ingresos = float(kpi_row.total_ingresos or 0)
    total_pedidos  = int(kpi_row.total_pedidos or 0)
    promedio       = (total_ingresos / total_pedidos) if total_pedidos else 0.0

    # ── 2. Top 10 productos más vendidos (últimos 30 días) ──
    desde_30d = datetime.now(timezone.utc).timestamp() - (30 * 24 * 60 * 60)
    desde_30d_dt = datetime.fromtimestamp(desde_30d, tz=timezone.utc)

    top_rows = session.exec(
        select(
            DetallePedido.nombre_snapshot,
            func.sum(DetallePedido.cantidad).label("cantidad"),
        )
        .join(Pedido, Pedido.id == DetallePedido.pedido_id)
        .where(
            Pedido.creado_en >= desde_30d_dt,
            Pedido.estado_codigo != "CANCELADO",
        )
        .group_by(DetallePedido.nombre_snapshot)
        .order_by(func.sum(DetallePedido.cantidad).desc())
        .limit(10)
    ).all()
    productos_mas_vendidos = [
        ProductoVendidoOut(nombre=row.nombre_snapshot, cantidad=int(row.cantidad))
        for row in top_rows
    ]

    # ── 3. Ingresos mensuales (últimos 12 meses) ──
    desde_12m = _rango_ultimos_meses(12)
    ing_rows = session.exec(
        select(
            func.extract("year", Pedido.creado_en).label("anio"),
            func.extract("month", Pedido.creado_en).label("mes"),
            func.sum(Pedido.total).label("ingreso"),
        )
        .where(
            Pedido.creado_en >= desde_12m,
            Pedido.estado_codigo != "CANCELADO",
        )
        .group_by("anio", "mes")
        .order_by("anio", "mes")
    ).all()
    ingresos_mensuales = [
        IngresoMensualOut(
            mes=MESES_ES[int(row.mes) - 1],
            anio=int(row.anio),
            ingreso=float(row.ingreso or 0),
        )
        for row in ing_rows
    ]

    # ── 4. Rentabilidad por producto (sobre todos los productos activos) ──
    productos_activos = session.exec(
        select(Producto)
        .where(Producto.eliminado_en == None, Producto.activo == True)  # noqa: E711
        .order_by(Producto.nombre)
    ).all()
    rentabilidad = []
    for p in productos_activos:
        costo = float(p.costo_produccion or 0)
        precio = float(p.precio or 0)
        if precio <= 0:
            continue
        margen_pct = ((precio - costo) / precio) * 100
        ganancia = precio - costo
        rentabilidad.append(RentabilidadOut(
            nombre=p.nombre,
            margen=round(margen_pct, 1),
            ganancia=round(ganancia, 2),
        ))
    # Ordenar por margen descendente
    rentabilidad.sort(key=lambda x: x.margen, reverse=True)

    return DashboardDataOut(
        total_ingresos=round(total_ingresos, 2),
        total_pedidos=total_pedidos,
        promedio_por_pedido=round(promedio, 2),
        productos_mas_vendidos=productos_mas_vendidos,
        ingresos_mensuales=ingresos_mensuales,
        rentabilidad_por_producto=rentabilidad,
    )


# ── Endpoints individuales (opcionales, por si se quieren usar aparte) ──
@router.get("/productos-mas-vendidos", response_model=List[ProductoVendidoOut])
def productos_mas_vendidos(
    limit: int = Query(10, ge=1, le=50),
    session: Session = Depends(get_session),
):
    desde_30d = datetime.now(timezone.utc).timestamp() - (30 * 24 * 60 * 60)
    desde_30d_dt = datetime.fromtimestamp(desde_30d, tz=timezone.utc)
    rows = session.exec(
        select(
            DetallePedido.nombre_snapshot,
            func.sum(DetallePedido.cantidad).label("cantidad"),
        )
        .join(Pedido, Pedido.id == DetallePedido.pedido_id)
        .where(
            Pedido.creado_en >= desde_30d_dt,
            Pedido.estado_codigo != "CANCELADO",
        )
        .group_by(DetallePedido.nombre_snapshot)
        .order_by(func.sum(DetallePedido.cantidad).desc())
        .limit(limit)
    ).all()
    return [ProductoVendidoOut(nombre=r.nombre_snapshot, cantidad=int(r.cantidad)) for r in rows]


@router.get("/ingresos-mensuales", response_model=List[IngresoMensualOut])
def ingresos_mensuales(
    meses: int = Query(12, ge=1, le=24),
    session: Session = Depends(get_session),
):
    desde = _rango_ultimos_meses(meses)
    rows = session.exec(
        select(
            func.extract("year", Pedido.creado_en).label("anio"),
            func.extract("month", Pedido.creado_en).label("mes"),
            func.sum(Pedido.total).label("ingreso"),
        )
        .where(
            Pedido.creado_en >= desde,
            Pedido.estado_codigo != "CANCELADO",
        )
        .group_by("anio", "mes")
        .order_by("anio", "mes")
    ).all()
    return [
        IngresoMensualOut(
            mes=MESES_ES[int(r.mes) - 1],
            anio=int(r.anio),
            ingreso=float(r.ingreso or 0),
        )
        for r in rows
    ]


@router.get("/rentabilidad", response_model=List[RentabilidadOut])
def rentabilidad_por_producto(session: Session = Depends(get_session)):
    productos = session.exec(
        select(Producto)
        .where(Producto.eliminado_en == None, Producto.activo == True)  # noqa: E711
    ).all()
    out = []
    for p in productos:
        precio = float(p.precio or 0)
        costo = float(p.costo_produccion or 0)
        if precio <= 0:
            continue
        margen = ((precio - costo) / precio) * 100
        out.append(RentabilidadOut(
            nombre=p.nombre,
            margen=round(margen, 1),
            ganancia=round(precio - costo, 2),
        ))
    out.sort(key=lambda x: x.margen, reverse=True)
    return out
