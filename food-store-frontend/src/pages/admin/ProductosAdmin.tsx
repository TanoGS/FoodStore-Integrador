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
  imagenes_url:      string[] | null;
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
    mutationFn: ({ id, payload }: { id?: number; payload: any }) =>
      id
        ? CatalogoService.actualizarProducto(id, payload)
        : CatalogoService.crearProducto(payload),
    onSuccess: (nuevoProducto) => {
      queryClient.setQueryData<Producto[]>(['productos'], (old = []) => {
        if (nuevoProducto.id) {
          // Editando: reemplazar en la lista
          return old.map(p => p.id === nuevoProducto.id ? nuevoProducto : p);
        } else {
          // Creando: agregar al inicio
          return [nuevoProducto, ...old];
        }
      });
      setIsModalOpen(false);
    },
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
  const [isLoadingEdit, setIsLoadingEdit] = useState(false);

  const abrirEditar = async (p: Producto) => {
    setIsLoadingEdit(true);
    try {
      const completo = await CatalogoService.getProductoById(p.id);
      setProductoEditando(completo);
      setIsModalOpen(true);
    } catch {
      alert('No se pudo cargar el producto para editar.');
    } finally {
      setIsLoadingEdit(false);
    }
  };
  const abrirNuevo = () => { setProductoEditando(null); setIsModalOpen(true); };

  const colSpan = puedeEditar ? 9 : 8;

  return (
    <div className="bg-slate-800 rounded-2xl border border-slate-700 p-6">

      {/* CABECERA */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
        <div>
          <h2 className="text-xl font-black text-white">Catálogo y Recetas</h2>
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
            className="border border-slate-600 rounded-xl px-4 py-2 text-sm bg-slate-700 text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-orange-500 w-full sm:w-60"
          />
          {puedeEditar && (
            <button
              onClick={abrirNuevo}
              className="flex items-center gap-1.5 bg-orange-600 hover:bg-orange-500 text-white px-4 py-2 rounded-xl font-bold text-sm transition-colors whitespace-nowrap"
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
            <tr className="bg-slate-900/80 text-slate-400 text-xs uppercase tracking-wider border-b border-slate-700">
              <th className="p-3 font-bold w-16">Img</th>
              <th className="p-3 font-bold">Nombre</th>
              <th className="p-3 font-bold text-right">Costo</th>
              <th className="p-3 font-bold text-right">Margen de Ganancia</th>
              <th className="p-3 font-bold text-right">Precio Final</th>
              <th className="p-3 font-bold text-center">Estado</th>
              {puedeEditar && <th className="p-3 font-bold text-center">Modificar</th>}
              <th className="p-3 font-bold">Fecha de Creación</th>
              <th className="p-3 font-bold">Última Modificación</th>
              <th className="p-3 font-bold text-center">Eliminado</th>
            </tr>
          </thead>

          <tbody className="divide-y divide-slate-700">
            {isLoading ? (
              <tr>
                <td colSpan={colSpan} className="p-8 text-center text-slate-400">
                  Cargando catálogo...
                </td>
              </tr>
            ) : paginados.length === 0 ? (
              <tr>
                <td colSpan={colSpan} className="p-8 text-center text-slate-500">
                  Sin resultados para "{filtroNombre}".
                </td>
              </tr>
            ) : (
              paginados.map((prod) => {
                const eliminado = prod.eliminado_en !== null;
                const rowCls = eliminado
                  ? 'bg-red-900/20 text-red-300'
                  : 'hover:bg-slate-700/30 text-slate-200';

                return (
                  <tr key={prod.id} className={`transition-colors ${rowCls}`}>

                    <td className="p-3">
                      {(prod.imagenes_url?.[0] ?? prod.imagen_url) ? (
                        <img
                          src={prod.imagenes_url?.[0] ?? prod.imagen_url!}
                          alt={prod.nombre}
                          className="w-12 h-12 rounded-lg object-cover border border-slate-600"
                          referrerPolicy="no-referrer"
                        />
                      ) : (
                        <div className="w-12 h-12 rounded-lg bg-slate-700 flex items-center justify-center text-slate-500 text-lg">
                          🍽️
                        </div>
                      )}
                    </td>

                    <td className="p-3">
                      <span className="font-bold text-white">{prod.nombre}</span>
                      {prod.stock_cantidad > 0 && (
                        <div className="text-[11px] text-slate-400 mt-0.5">
                          {prod.stock_cantidad} en stock
                        </div>
                      )}
                    </td>

                    <td className="p-3 text-right font-medium text-slate-400">
                      ${prod.costo_produccion.toFixed(2)}
                    </td>

                    <td className={`p-3 text-right font-bold ${eliminado ? 'text-slate-500' : 'text-orange-400'}`}>
                      <span className="inline-flex items-center gap-0.5">
                        <ArrowUpRight className="h-3.5 w-3.5" />
                        {prod.margen_ganancia}%
                      </span>
                    </td>

                    <td className={`p-3 text-right font-black text-lg ${eliminado ? 'text-slate-500' : 'text-green-400'}`}>
                      ${prod.precio.toFixed(2)}
                    </td>

                    <td className="p-3 text-center">
                      {puedeEditar && !eliminado ? (
                        <button
                          onClick={() => mutToggleActivo.mutate({ id: prod.id, activo: !prod.activo })}
                          title={prod.activo ? 'Ocultar del catálogo' : 'Mostrar en catálogo'}
                        >
                          {prod.activo
                            ? <ToggleRight className="h-8 w-8 text-green-400 mx-auto" />
                            : <ToggleLeft  className="h-8 w-8 text-slate-500 mx-auto" />}
                        </button>
                      ) : (
                        <span className={`text-[10px] font-black px-2 py-0.5 rounded-full ${prod.activo ? 'bg-green-900/40 text-green-400 border border-green-700/50' : 'bg-slate-700 text-slate-400 border border-slate-600'}`}>
                          {prod.activo ? 'En Menú' : 'Oculto'}
                        </span>
                      )}
                    </td>

                    {puedeEditar && (
                      <td className="p-3 text-center">
                        {!eliminado && (
                          <button
                            onClick={() => abrirEditar(prod)}
                            title="Editar producto"
                            className="p-1.5 text-blue-400 hover:bg-blue-900/30 rounded-lg transition-colors"
                          >
                            <Edit className="h-4 w-4" />
                          </button>
                        )}
                      </td>
                    )}

                    <td className="p-3 text-xs whitespace-nowrap text-slate-400">
                      {fmtFecha(prod.creado_en)}
                    </td>
                    <td className="p-3 text-xs whitespace-nowrap text-slate-400">
                      {fmtFecha(prod.actualizado_en)}
                    </td>

                    <td className="p-3 text-center">
                      {eliminado ? (
                        <div className="flex flex-col items-center gap-1">
                          <span className="text-[10px] font-bold text-red-400 whitespace-nowrap">
                            {fmtFecha(prod.eliminado_en)}
                          </span>
                          {puedeEditar && (
                            <button
                              onClick={() => mutReactivar.mutate(prod.id)}
                              className="flex items-center gap-1 text-[10px] font-bold px-2 py-1 rounded-lg bg-green-900/40 text-green-400 border border-green-700/50 hover:bg-green-900/60 transition-colors"
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
                            className="flex items-center gap-1 text-[10px] font-bold px-2 py-1 rounded-lg bg-slate-700 text-slate-400 hover:bg-red-900/40 hover:text-red-400 transition-colors"
                          >
                            <Trash2 className="h-3 w-3" /> Eliminar
                          </button>
                        ) : (
                          <span className="text-[10px] text-slate-500">Activo</span>
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
        <div className="flex items-center justify-between mt-5 pt-4 border-t border-slate-700">
          <span className="text-sm text-slate-400">
            Pág. {paginaActual} / {totalPaginas}
            <span className="ml-2 text-slate-500">({filtrados.length} total)</span>
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setPagina(p => Math.max(1, p - 1))}
              disabled={paginaActual === 1}
              className="p-2 rounded-lg border border-slate-600 text-slate-400 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <button
              onClick={() => setPagina(p => Math.min(totalPaginas, p + 1))}
              disabled={paginaActual === totalPaginas}
              className="p-2 rounded-lg border border-slate-600 text-slate-400 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed"
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
          onSave={(payload: any) => mutGuardar.mutate({
            id: productoEditando?.id,
            payload,
          })}
          productoEditar={productoEditando}
          isSaving={mutGuardar.isPending}
        />
      )}
    </div>
  );
}
