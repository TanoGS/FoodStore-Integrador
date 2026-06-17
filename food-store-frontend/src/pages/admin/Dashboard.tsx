import { useEffect, useState } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, Legend, Cell,
} from 'recharts';
import { TrendingUp, Package, DollarSign, ShoppingCart, Loader2 } from 'lucide-react';
import { DashboardService } from '../../services/dashboard.service';
import type { DashboardData } from '../../types/dashboard.type';

const fmtARS = (n: number) =>
  new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS', maximumFractionDigits: 0 })
    .format(n);

// Paleta de colores consistente con el resto del admin (naranja = primary)
const COLORS = ['#f97316', '#fb923c', '#fdba74', '#fed7aa', '#ffedd5', '#c2410c', '#9a3412', '#7c2d12'];

const KpiCard = ({
  icon: Icon, label, value, sub, color,
}: { icon: React.ComponentType<{ className?: string }>; label: string; value: string; sub?: string; color: string }) => (
  <div className="bg-slate-800 rounded-2xl border border-slate-700 p-6 shadow-lg">
    <div className="flex items-center justify-between mb-3">
      <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">{label}</span>
      <div className={`p-2 rounded-lg ${color}`}>
        <Icon className="w-5 h-5 text-white" />
      </div>
    </div>
    <div className="text-2xl font-black text-white">{value}</div>
    {sub && <div className="text-xs text-slate-400 mt-1">{sub}</div>}
  </div>
);

const ChartCard = ({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) => (
  <div className="bg-slate-800 rounded-2xl border border-slate-700 p-6 shadow-lg">
    <div className="mb-4">
      <h3 className="text-lg font-black text-white">{title}</h3>
      {subtitle && <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>}
    </div>
    <div style={{ width: '100%', height: 320 }}>
      {children}
    </div>
  </div>
);

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    DashboardService.obtenerDatos()
      .then((d) => { if (mounted) { setData(d); setLoading(false); } })
      .catch(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, []);

  if (loading || !data) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <Loader2 className="w-10 h-10 text-orange-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-3xl font-black text-white">Dashboard</h1>
        <p className="text-slate-400 mt-1">Resumen de ventas, ingresos y rentabilidad</p>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          icon={DollarSign}
          label="Ingresos anuales"
          value={fmtARS(data.totalIngresos)}
          sub="Acumulado 2026"
          color="bg-orange-600"
        />
        <KpiCard
          icon={ShoppingCart}
          label="Pedidos totales"
          value={data.totalPedidos.toLocaleString('es-AR')}
          sub="En el año"
          color="bg-blue-600"
        />
        <KpiCard
          icon={TrendingUp}
          label="Ticket promedio"
          value={fmtARS(data.promedioPorPedido)}
          sub="Por pedido"
          color="bg-green-600"
        />
        <KpiCard
          icon={Package}
          label="Productos vendidos"
          value={data.productosMasVendidos.reduce((a, b) => a + b.cantidad, 0).toLocaleString('es-AR')}
          sub="Top 10 (últimos 30 días)"
          color="bg-purple-600"
        />
      </div>

      {/* Gráficos */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 1. Ingresos mensuales */}
        <ChartCard title="Ingresos mensuales" subtitle="Evolución año 2026">
          <ResponsiveContainer>
            <LineChart data={data.ingresosMensuales} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="mes" stroke="#94a3b8" style={{ fontSize: 11 }} />
              <YAxis
                stroke="#94a3b8"
                style={{ fontSize: 11 }}
                tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
              />
              <Tooltip
                contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: 8 }}
                labelStyle={{ color: '#f1f5f9' }}
                formatter={(v: any) => fmtARS(Number(v))}
              />
              <Legend wrapperStyle={{ color: '#94a3b8', fontSize: 12 }} />
              <Line
                type="monotone"
                dataKey="ingreso"
                name="Ingreso"
                stroke="#f97316"
                strokeWidth={3}
                dot={{ fill: '#f97316', r: 4 }}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* 2. Productos más vendidos */}
        <ChartCard title="Productos más vendidos" subtitle="Top 10 — últimos 30 días">
          <ResponsiveContainer>
            <BarChart
              data={data.productosMasVendidos}
              layout="vertical"
              margin={{ top: 5, right: 20, left: 0, bottom: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis type="number" stroke="#94a3b8" style={{ fontSize: 11 }} />
              <YAxis
                type="category"
                dataKey="nombre"
                stroke="#94a3b8"
                style={{ fontSize: 11 }}
                width={130}
              />
              <Tooltip
                contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: 8 }}
                labelStyle={{ color: '#f1f5f9' }}
              />
              <Bar dataKey="cantidad" name="Unidades vendidas" radius={[0, 6, 6, 0]}>
                {data.productosMasVendidos.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      {/* 3. Rentabilidad por producto */}
      <ChartCard
        title="Rentabilidad por producto"
        subtitle="Margen % sobre precio de venta"
      >
        <ResponsiveContainer>
          <BarChart
            data={data.rentabilidadPorProducto}
            margin={{ top: 10, right: 20, left: 0, bottom: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis
              dataKey="nombre"
              stroke="#94a3b8"
              style={{ fontSize: 10 }}
              angle={-20}
              textAnchor="end"
              height={70}
            />
            <YAxis
              stroke="#94a3b8"
              style={{ fontSize: 11 }}
              tickFormatter={(v) => `${v}%`}
            />
            <Tooltip
              contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: 8 }}
              labelStyle={{ color: '#f1f5f9' }}
              formatter={(v: any, _name: any, props: any) => [
                `${v}% (${fmtARS(props?.payload?.ganancia)} c/u)`,
                'Margen',
              ]}
            />
            <Bar dataKey="margen" name="Margen %" radius={[6, 6, 0, 0]}>
              {data.rentabilidadPorProducto.map((p, i) => (
                <Cell
                  key={i}
                  fill={p.margen >= 50 ? '#10b981' : p.margen >= 30 ? '#f97316' : '#ef4444'}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>
    </div>
  );
}
