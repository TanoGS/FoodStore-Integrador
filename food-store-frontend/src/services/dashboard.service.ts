import api from '../config/axios';
import type { DashboardData } from '../types/dashboard.type';

/**
 * Servicio de Dashboard.
 * Conecta con el backend real en /api/v1/admin/dashboard.
 * - GET /admin/dashboard                         → datos completos (1 sola llamada)
 * - GET /admin/dashboard/productos-mas-vendidos  → top N
 * - GET /admin/dashboard/ingresos-mensuales      → serie temporal
 * - GET /admin/dashboard/rentabilidad            → margen por producto
 */
export const DashboardService = {
  /** Devuelve KPIs + los 3 datasets para los gráficos en una sola respuesta. */
  obtenerDatos: async (): Promise<DashboardData> => {
    const res = await api.get<any>('/admin/dashboard');
    // El backend devuelve snake_case (total_ingresos, productos_mas_vendidos...)
    // Adaptamos al shape camelCase esperado por el frontend.
    return {
      totalIngresos:          Number(res.data.total_ingresos ?? 0),
      totalPedidos:           Number(res.data.total_pedidos ?? 0),
      promedioPorPedido:      Number(res.data.promedio_por_pedido ?? 0),
      productosMasVendidos:   (res.data.productos_mas_vendidos ?? []).map((p: any) => ({
        nombre:   p.nombre,
        cantidad: Number(p.cantidad),
      })),
      ingresosMensuales:      (res.data.ingresos_mensuales ?? []).map((m: any) => ({
        mes:     m.mes,
        anio:    Number(m.anio),
        ingreso: Number(m.ingreso),
      })),
      rentabilidadPorProducto: (res.data.rentabilidad_por_producto ?? []).map((r: any) => ({
        nombre:   r.nombre,
        margen:   Number(r.margen),
        ganancia: Number(r.ganancia),
      })),
    };
  },
};
