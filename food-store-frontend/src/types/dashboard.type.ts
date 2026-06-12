export interface ProductoVendido {
  nombre: string;
  cantidad: number;
}

export interface IngresoMensual {
  mes: string;
  ingreso: number;
  anio: number;
}

export interface RentabilidadProducto {
  nombre: string;
  margen: number; // porcentaje
  ganancia: number; // $ por unidad
}

export interface DashboardData {
  productosMasVendidos: ProductoVendido[];
  ingresosMensuales: IngresoMensual[];
  rentabilidadPorProducto: RentabilidadProducto[];
  totalIngresos: number;
  totalPedidos: number;
  promedioPorPedido: number;
}
