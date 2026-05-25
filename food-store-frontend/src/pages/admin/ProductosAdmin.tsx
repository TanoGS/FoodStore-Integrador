import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Plus, Edit, ToggleLeft, ToggleRight, Trash2, RotateCcw,
  ChevronLeft, ChevronRight, ArrowUpRight,
} from 'lucide-react';
import { CatalogoService } from '../../services/catalogo.service';
import ProductoModal from '../../components/admin/ProductoModal';
import { useRole } from '../../hooks/useRole';

// ── TypeScript ─────────────────────────────────────────────────────────────────
interface Producto {
  id:               number;
  nombre:           string;
  descripcion:      string | null;
  imagen_url:       string | null;
  activo:           boolean;
  costo_produccion: number;
  margen_ganancia:  number;
  precio:           number;
  stock_cantidad:   number;
  creado_en:        string;
  actualizado_en:   string;
  eliminado_en:     string | null;
}

const ITEMS_POR_PAGINA = 10;

const fmtFecha = (d: string | null | undefined) =>
  d
    ? new Date(d).toLocaleString('es-AR', {
        day: '2-digit', month: '2-digit', year: '2-digit',
        hour: '2-digit', minute: '2-digit',
      })
    : '—';

export default function ProductosAdmin() {
  const queryClient = useQueryClient();
  const { puedeEditar } = useRole();

  const [filtroNombre, setFiltroNombre]   = useState('');
  const [pagina, setPagina]               = useState(1);
  const [isModalOpen, setIsModalOpen]     = useState(false);
  const [productoEditando, setProductoEditando] = useState<Producto | null>(null);

  // ── SERVER STATE ───────────────────────────────────────────────────────────
  const { data: productos = [], isLoading } = useQuery<Producto[]>({
    queryKey: ['productos'],
    queryFn:  CatalogoService.getProductosTodos,
  });

  // ── FILTRADO + PAGINACIÓN (client-side) ────────────────────────────────────
  const filtrados = useMemo(() => {
    const lower = filtroNombre.toLowerCase().trim();
    return lower
      ? productos.filter(p => p.nombre.toLowerCase().includes(lower))
      : productos;
  }, [productos, filtroNombre]);

  const totalPaginas = Math.max(1, Math.ceil(filtrados.length / ITEMS_POR_PAGINA));
  const paginaActual = Math.min(pagina, totalPaginas);
  const paginados    = filtrados.slice(
    (paginaActual - 1) * ITEMS_POR_PAGINA,
    paginaActual * ITEMS_POR_PAGINA,
  );

  // ── MUTATIONS ──────────────────────────────────────────────────────────────
  const invalidar = () => queryClient.invalidateQueries({ queryKey: ['productos'] });

  const mutGuardar = useMutation({
    mutationFn: (payload: any) =>
      productoEditando
        ? CatalogoService.actualizarProducto(productoEditando.id, payload)
        : CatalogoService.crearProducto(payload),
    onSuccess: () => { invalidar(); setIsModalOpen(false); },
    onError: (e: any) =>
      alert(`Error: ${e.response?.data?.detail || 'No se pudo guardar el producto'}`),
  });

  const mutToggleActivo = useMutation({
    mutationFn: ({ id, activo }: { id: number; activo: boolean }) =>
      CatalogoService.toggleDisponibilidad(id, activo),
    onSuccess: invalidar,
    onError: () => alert('Error al cambiar la disponibilidad.'),
  });

  const mutEliminar = useMutation({
    mutationFn: (id: number) => CatalogoService.eliminarProducto(id),
    onSuccess: invalidar,
    onError: (e: any) =>
      alert(`No se pudo eliminar: ${e.response?.data?.detail || 'error desconocido'}`),
  });

  const mutReactivar = useMutation({
    mutationFn: (id: number) => CatalogoService.reactivarProducto(id),
    onSuccess: invalidar,
    onError: () => alert('No se pudo reactivar el producto.'),
  });

  // ── Helpers UI ──────────────────────────────────────────────────────────────
  const handleFiltro = (v: string) => { setFiltroNombre(v); setPagina(1); };
  const abrirEditar  = (p: Producto) => { setProductoEditando(p); setIsModalOpen(true); };
  const abrirNuevo   = () => { setProductoEditando(null); setIsModalOpen(true); };

  const colSpan = puedeEditar ? 9 : 8;

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

      {/* CABECERA */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
        <div>
          <h2 className="text-xl font-black text-slate-800">Catálogo y Recetas</h2>
          <p className="text-slate-400 text-sm mt-0.5">
            {filtrados.length} producto{filtrados.length !== 1 ? 's' : ''} encontrado{filtrados.length !== 1 ? 's' : ''}
          </p>
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          <input
            type="text"
            placeholder="Buscar por nombre..."
            value={filtroNombre}
            onChange={e => handleFiltro(e.target.value)}
            className="border border-slate-200 rounded-xl px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-300 w-full sm:w-60"
          />
          {puedeEditar && (
            <button
              onClick={abrirNuevo}
              className="flex items-center gap-1.5 bg-orange-600 hover:bg-orange-700 text-white px-4 py-2 rounded-xl font-bold text-sm transition-colors whitespace-nowrap"
            >
              <Plus className="h-4 w-4" /> Nuevo
            </button>
          )}
        </div>
      </div>

      {/* TABLA */}
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse text-sm">
          <thead>
            <tr className="bg-gray-50 text-gray-500 text-xs uppercase tracking-wider border-b border-gray-200">
              <th className="p-3 font-semibold">Nombre</th>
              <th className="p-3 font-semibold text-right">Costo</th>
              <th className="p-3 font-semibold text-right">Margen de Ganancia</th>
              <th className="p-3 font-semibold text-right">Precio Final</th>
              <th className="p-3 font-semibold text-center">Estado</th>
              {puedeEditar && <th className="p-3 font-semibold text-center">Modificar</th>}
              <th className="p-3 font-semibold">Fecha de Creación</th>
              <th className="p-3 font-semibold">Última Modificación</th>
              <th className="p-3 font-semibold text-center">Eliminado</th>
            </tr>
          </thead>

          <tbody className="divide-y divide-gray-100">
            {isLoading ? (
              <tr>
                <td colSpan={colSpan} className="p-8 text-center text-gray-500">
                  Cargando catálogo...
                </td>
              </tr>
            ) : paginados.length === 0 ? (
              <tr>
                <td colSpan={colSpan} className="p-8 text-center text-gray-400">
                  Sin resultados para "{filtroNombre}".
                </td>
              </tr>
            ) : (
              paginados.map((prod) => {
                const eliminado = prod.eliminado_en !== null;
                const rowCls = eliminado
                  ? 'bg-red-50 text-red-800'
                  : 'hover:bg-gray-50 text-gray-800';

                return (
                  <tr key={prod.id} className={`transition-colors ${rowCls}`}>

                    {/* Nombre */}
                    <td className="p-3">
                      <span className="font-bold">{prod.nombre}</span>
                      {prod.stock_cantidad > 0 && (
                        <div className="text-[11px] text-slate-400 mt-0.5">
                          {prod.stock_cantidad} en stock
                        </div>
                      )}
                    </td>

                    <td className="p-3 text-right font-medium text-slate-500">
                      ${prod.costo_produccion.toFixed(2)}
                    </td>

                    <td className={`p-3 text-right font-bold ${eliminado ? '' : 'text-orange-600'}`}>
                      <span className="inline-flex items-center gap-0.5">
                        <ArrowUpRight className="h-3.5 w-3.5" />
                        {prod.margen_ganancia}%
                      </span>
                    </td>

                    <td className={`p-3 text-right font-black text-lg ${eliminado ? '' : 'text-green-600'}`}>
                      ${prod.precio.toFixed(2)}
                    </td>

                    {/* Estado: toggle activo/inactivo */}
                    <td className="p-3 text-center">
                      {puedeEditar && !eliminado ? (
                        <button
                          onClick={() => mutToggleActivo.mutate({ id: prod.id, activo: !prod.activo })}
                          title={prod.activo ? 'Ocultar del catálogo' : 'Mostrar en catálogo'}
                        >
                          {prod.activo
                            ? <ToggleRight className="h-8 w-8 text-green-500 mx-auto" />
                            : <ToggleLeft  className="h-8 w-8 text-gray-400 mx-auto" />}
                        </button>
                      ) : (
                        <span className={`text-[10px] font-black px-2 py-0.5 rounded-full ${prod.activo ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-500'}`}>
                          {prod.activo ? 'En Menú' : 'Oculto'}
                        </span>
                      )}
                    </td>

                    {/* Botón Modificar */}
                    {puedeEditar && (
                      <td className="p-3 text-center">
                        {!eliminado && (
                          <button
                            onClick={() => abrirEditar(prod)}
                            title="Editar producto"
                            className="p-1.5 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                          >
                            <Edit className="h-4 w-4" />
                          </button>
                        )}
                      </td>
                    )}

                    {/* Fechas */}
                    <td className="p-3 text-xs whitespace-nowrap text-gray-500">
                      {fmtFecha(prod.creado_en)}
                    </td>
                    <td className="p-3 text-xs whitespace-nowrap text-gray-500">
                      {fmtFecha(prod.actualizado_en)}
                    </td>

                    {/* Columna Eliminado: toggle on/off */}
                    <td className="p-3 text-center">
                      {eliminado ? (
                        <div className="flex flex-col items-center gap-1">
                          <span className="text-[10px] font-bold text-red-600 whitespace-nowrap">
                            {fmtFecha(prod.eliminado_en)}
                          </span>
                          {puedeEditar && (
                            <button
                              onClick={() => mutReactivar.mutate(prod.id)}
                              className="flex items-center gap-1 text-[10px] font-bold px-2 py-1 rounded-lg bg-green-100 text-green-700 hover:bg-green-200 transition-colors"
                            >
                              <RotateCcw className="h-3 w-3" /> Reactivar
                            </button>
                          )}
                        </div>
                      ) : (
                        puedeEditar ? (
                          <button
                            onClick={() => {
                              if (window.confirm(`¿Eliminar "${prod.nombre}"?\nPodrás reactivarlo después.`)) {
                                mutEliminar.mutate(prod.id);
                              }
                            }}
                            title="Dar de baja"
                            className="flex items-center gap-1 text-[10px] font-bold px-2 py-1 rounded-lg bg-slate-100 text-slate-500 hover:bg-red-100 hover:text-red-600 transition-colors"
                          >
                            <Trash2 className="h-3 w-3" /> Eliminar
                          </button>
                        ) : (
                          <span className="text-[10px] text-gray-400">Activo</span>
                        )
                      )}
                    </td>

                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* PAGINACIÓN */}
      {totalPaginas > 1 && (
        <div className="flex items-center justify-between mt-5 pt-4 border-t border-slate-100">
          <span className="text-sm text-slate-500">
            Pág. {paginaActual} / {totalPaginas}
            <span className="ml-2 text-slate-400">({filtrados.length} total)</span>
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setPagina(p => Math.max(1, p - 1))}
              disabled={paginaActual === 1}
              className="p-2 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <button
              onClick={() => setPagina(p => Math.min(totalPaginas, p + 1))}
              disabled={paginaActual === totalPaginas}
              className="p-2 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* MODAL */}
      {isModalOpen && (
        <ProductoModal
          onClose={() => setIsModalOpen(false)}
          onSave={(payload: any) => mutGuardar.mutate(payload)}
          productoEditar={
            productoEditando
              ? {
                  id:              productoEditando.id,
                  nombre:          productoEditando.nombre,
                  descripcion:     productoEditando.descripcion ?? undefined,
                  imagen_url:      productoEditando.imagen_url ?? null,
                  stock:           productoEditando.stock_cantidad,
                  activo:          productoEditando.activo,
                  margen_ganancia: productoEditando.margen_ganancia,
                  precio:          productoEditando.precio,
                }
              : null
          }
        />
      )}
    </div>
  );
}
