"""
Utilidades de stock para el módulo de pedidos.

Extraídas del servicio para que puedan ser consumidas por otros módulos
(p.ej. pagos) sin crear una dependencia service→service.

Flujo correcto: pagos/service.py → pedido/stock.py (utilidad)
                pedido/service.py → pedido/stock.py (utilidad)
"""
from typing import List

from sqlmodel import Session

from app.modules.catalogo.ingrediente.repository import IngredienteRepository
from app.modules.catalogo.producto.repository import ProductoRepository
from app.modules.pedido.models import Pedido
from app.modules.pedido.schemas import PedidoCreate
from core.exceptions import ConflictError


def descontar_stock(session: Session, pedido: Pedido) -> List[dict]:
    """
    Descuenta stock de ingredientes al confirmar un pedido.
    Se llama cuando el pedido pasa a CONFIRMADO.

    Valida stock suficiente antes de aplicar cambios;
    si falta stock lanza ConflictError sin aplicar ningún descuento.

    Returns:
        Lista de dicts con {tipo, id, nombre, stock_anterior, stock_nuevo}.
    """
    producto_repo = ProductoRepository(session)
    ingrediente_repo = IngredienteRepository(session)

    # Pre-validación
    faltantes: List[dict] = []
    for detalle in pedido.detalles:
        producto = producto_repo.get_by_id(detalle.producto_id)
        if not producto:
            continue
        removidos = set(detalle.personalizacion or [])
        for enlace in producto.ingredientes_enlaces:
            if enlace.ingrediente_id in removidos:
                continue
            ingrediente = ingrediente_repo.get_by_id(enlace.ingrediente_id)
            if not ingrediente:
                continue
            cantidad_requerida = float(enlace.cantidad_requerida) * detalle.cantidad
            if ingrediente.stock < cantidad_requerida:
                faltantes.append({
                    "tipo": "INGREDIENTE",
                    "id": ingrediente.id,
                    "nombre": ingrediente.nombre,
                    "requerido": cantidad_requerida,
                    "disponible": ingrediente.stock,
                })

    if faltantes:
        raise ConflictError(
            f"stock_insuficiente_al_confirmar: pedido_id={pedido.id}"
        )

    # Descuento real
    cambios: List[dict] = []
    for detalle in pedido.detalles:
        producto = producto_repo.get_by_id(detalle.producto_id)
        if not producto:
            continue
        removidos = set(detalle.personalizacion or [])
        for enlace in producto.ingredientes_enlaces:
            if enlace.ingrediente_id in removidos:
                continue
            ingrediente = ingrediente_repo.get_by_id(enlace.ingrediente_id)
            if not ingrediente:
                continue
            cantidad_a_restar = float(enlace.cantidad_requerida) * detalle.cantidad
            stock_anterior = float(ingrediente.stock)
            ingrediente.stock = max(0.0, float(ingrediente.stock) - cantidad_a_restar)
            session.add(ingrediente)
            cambios.append({
                "tipo": "INGREDIENTE",
                "id": ingrediente.id,
                "nombre": ingrediente.nombre,
                "stock_anterior": stock_anterior,
                "stock_nuevo": float(ingrediente.stock),
            })

    return cambios


def devolver_stock(session: Session, pedido: Pedido) -> List[dict]:
    """
    Devuelve stock de ingredientes al cancelar un pedido que ya fue confirmado.

    Returns:
        Lista de dicts con {tipo, id, nombre, stock_anterior, stock_nuevo}.
    """
    producto_repo = ProductoRepository(session)
    ingrediente_repo = IngredienteRepository(session)

    cambios: List[dict] = []
    for detalle in pedido.detalles:
        producto = producto_repo.get_by_id(detalle.producto_id)
        if not producto:
            continue
        removidos = set(detalle.personalizacion or [])
        for enlace in producto.ingredientes_enlaces:
            if enlace.ingrediente_id in removidos:
                continue
            ingrediente = ingrediente_repo.get_by_id(enlace.ingrediente_id)
            if not ingrediente:
                continue
            cantidad_a_devolver = float(enlace.cantidad_requerida) * detalle.cantidad
            stock_anterior = float(ingrediente.stock)
            ingrediente.stock = float(ingrediente.stock) + cantidad_a_devolver
            session.add(ingrediente)
            cambios.append({
                "tipo": "INGREDIENTE",
                "id": ingrediente.id,
                "nombre": ingrediente.nombre,
                "stock_anterior": stock_anterior,
                "stock_nuevo": float(ingrediente.stock),
            })

    return cambios


def detectar_stock_bajo(session: Session, cambios_stock: List[dict]) -> List[dict]:
    """
    Dado el resultado de descontar_stock, retorna los ingredientes cuyo
    stock quedó por debajo de su umbral de seguridad.

    Returns:
        Lista de dicts con {id, nombre, stock_actual, stock_seguridad, unidad}.
    """
    ingrediente_repo = IngredienteRepository(session)

    criticos: List[dict] = []
    for cambio in cambios_stock:
        if cambio["tipo"] != "INGREDIENTE":
            continue
        ingrediente = ingrediente_repo.get_by_id(cambio["id"])
        if not ingrediente:
            continue
        seguridad = getattr(ingrediente, "stock_seguridad", None)
        if seguridad is None:
            continue
        if float(ingrediente.stock) < float(seguridad):
            criticos.append({
                "id": ingrediente.id,
                "nombre": ingrediente.nombre,
                "stock_actual": float(ingrediente.stock),
                "stock_seguridad": float(seguridad),
                "unidad": getattr(ingrediente, "unidad", "u"),
            })

    return criticos


def obtener_resumen_stock_preview(session: Session, datos: PedidoCreate) -> List[dict]:
    """
    Valida disponibilidad de stock ANTES de crear el pedido (sin persistir nada).
    Retorna lista de faltantes (vacía si todo OK).
    """
    producto_repo = ProductoRepository(session)
    ingrediente_repo = IngredienteRepository(session)

    resumen: List[dict] = []
    for item in datos.detalles:
        producto = producto_repo.get_by_id(item.producto_id)
        if not producto:
            continue
        removidos = set(item.personalizacion or [])
        for enlace in producto.ingredientes_enlaces:
            if enlace.ingrediente_id in removidos:
                continue
            ingrediente = ingrediente_repo.get_by_id(enlace.ingrediente_id)
            if not ingrediente:
                continue
            requerido = float(enlace.cantidad_requerida) * item.cantidad
            disponible = float(ingrediente.stock)
            if disponible < requerido:
                resumen.append({
                    "tipo": "INGREDIENTE",
                    "id": ingrediente.id,
                    "nombre": ingrediente.nombre,
                    "requerido": requerido,
                    "disponible": disponible,
                    "ok": False,
                })

    return resumen
