"""
Configuración mutable en tiempo de ejecución.

Valores que el staff puede cambiar desde el panel admin sin reiniciar el servidor.
Se almacenan en memoria: se resetean al reiniciar con el valor por defecto.
"""

# Costo de envío para pedidos DELIVERY (en ARS)
_costo_envio_delivery: float = 50.0


def get_costo_envio_delivery() -> float:
    return _costo_envio_delivery


def set_costo_envio_delivery(valor: float) -> None:
    global _costo_envio_delivery
    _costo_envio_delivery = valor
