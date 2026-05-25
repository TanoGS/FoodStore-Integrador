import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Plus, Edit, ToggleLeft, ToggleRight, Trash2, RotateCcw,
  ChevronLeft, ChevronRight, Layers,
} from 'lucide-react';
import { CatalogoService } from '../../services/catalogo.service';
import CategoriaModal from '../../components/admin/CategoriaModal';
import { useRole } from '../../hooks/useRole';

// ── TypeScript ─────────────────────────────────────────────────────────────────
interface Subcategoria {
  id:     number;
  nombre: string;
}

interface Categoria {
  id:              number;
  nombre:          string;
  activo:          boolean;
  parent_id:       number | null;
  subcategorias:   Subcategoria[];
  creado_en:       string;
  actualizado_en:  string;
  eliminado_en:    string | null;
}

const ITEMS_POR_PAGINA = 10;

const fmtFecha = (d: string | null | undefined) =>
  d
    ? new Date(d).toLocaleString('es-AR', {
        day: '2-digit', month: '2-digit', year: '2-digit',
        hour: '2-digit', minute: '2-digit',
      })
    : '—';

export default function CategoriasAdmin() {
  const queryClient = useQueryClient();
  const { puedeEditar } = useRole();

  const [filtroNombre, setFiltroNombre]     = useState('');
  const [pagina, setPagina]                 = useState(1);
  const [isModalOpen, setIsModalOpen]       = useState(false);
  const [categoriaEditando, setCategoriaEditando] = useState<Categoria | null>(null);

  // ── SERVER STATE ───────────────────────────────────────────────────────────
  const { data: categorias = [], isLoading } = useQuery<Categoria[]>({
    queryKey: ['categorias'],
    queryFn:  CatalogoService.getCategoriasTodas,
  });

  // ── FILTRADO + PAGINACIÓN (client-side) ────────────────────────────────────
  const filtradas = useMemo(() => {
    const lower = filtroNombre.toLowerCase().trim();
    return lower
      ? categorias.filter(c => c.nombre.toLowerCase().includes(lower))
      : categorias;
  }, [categorias, filtroNombre]);

  const totalPaginas = Math.max(1, Math.ceil(filtradas.length / ITEMS_POR_PAGINA));
  const paginaActual = Math.min(pagina, totalPaginas);
  const paginadas    = filtradas.slice(
    (paginaActual - 1) * ITEMS_POR_PAGINA,
    paginaActual * ITEMS_POR_PAGINA,
  );

  // ── MUTATIONS ──────────────────────────────────────────────────────────────
  const invalidar = () => queryClient.invalidateQueries({ queryKey: ['categorias'] });

  const mutGuardar = useMutation({
    mutationFn: (payload: any) =>
      categoriaEditando
        ? CatalogoService.actualizarCategoria(categoriaEditando.id, payload)
        : CatalogoService.crearCategoria(payload),
    onSuccess: () => { invalidar(); setIsModalOpen(false); },
    onError: (e: any) =>
      alert(`Error: ${e.response?.data?.detail || 'No se pudo guardar'}`),
  });

  const mutToggleActivo = useMutation({
    mutationFn: ({ id, activo }: { id: number; activo: boolean }) =>
      CatalogoService.actualizarCategoria(id, { activo }),
    onSuccess: invalidar,
    onError: () => alert('Error al cambiar la visibilidad.'),
  });

  const mutEliminar = useMutation({
    mutationFn: (id: number) => CatalogoService.eliminarCategoria(id),
    onSuccess: invalidar,
    onError: (e: any) =>
      alert(`No se pudo eliminar: ${e.response?.data?.detail || 'error desconocido'}`),
  });

  const mutReactivar = useMutation({
    mutationFn: (id: number) => CatalogoService.reactivarCategoria(id),
    onSuccess: invalidar,
    onError: (e: any) =>
      alert(`No se pudo reactivar: ${e.response?.data?.detail || 'error desconocido'}`),
  });

  // ── Helpers UI ──────────────────────────────────────────────────────────────
  const handleFiltro = (v: string) => { setFiltroNombre(v); setPagina(1); };
  const abrirEditar  = (cat: Categoria) => { setCategoriaEditando(cat); setIsModalOpen(true); };
  const abrirNuevo   = () => { setCategoriaEditando(null); setIsModalOpen(true); };

  const colSpan = puedeEditar ? 6 : 5;

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

      {/* CABECERA */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
        <div>
          <h2 className="text-xl font-black text-slate-800">Categorías</h2>
          <p className="text-slate-400 text-sm mt-0.5">
            {filtradas.length} categoría{filtradas.length !== 1 ? 's' : ''} encontrada{filtradas.length !== 1 ? 's' : ''}
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
              <Plus className="h-4 w-4" /> Nueva
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
                  Cargando categorías...
                </td>
              </tr>
            ) : paginadas.length === 0 ? (
              <tr>
                <td colSpan={colSpan} className="p-8 text-center text-gray-400">
                  Sin resultados para "{filtroNombre}".
                </td>
              </tr>
            ) : (
              paginadas.map((cat) => {
                const eliminada = cat.eliminado_en !== null;
                const rowCls = eliminada
                  ? 'bg-red-50 text-red-800'
                  : 'hover:bg-gray-50 text-gray-800';

                return (
                  <tr key={cat.id} className={`transition-colors ${rowCls}`}>

                    {/* Nombre + subcategorías */}
                    <td className="p-3">
                      <span className="font-bold">{cat.nombre}</span>
                      {cat.parent_id && (
                        <span className="ml-2 text-[10px] text-slate-400 italic">sub-categoría</span>
                      )}
                      {cat.subcategorias?.length > 0 && (
                        <div className="flex items-center gap-1 text-[11px] text-blue-500 mt-0.5">
                          <Layers className="h-3 w-3" />
                          {cat.subcategorias.length} sub-categoría{cat.subcategorias.length !== 1 ? 's' : ''}
                        </div>
                      )}
                    </td>

                    {/* Estado: toggle visible/oculto */}
                    <td className="p-3 text-center">
                      {puedeEditar && !eliminada ? (
                        <button
                          onClick={() => mutToggleActivo.mutate({ id: cat.id, activo: !cat.activo })}
                          title={cat.activo ? 'Ocultar del catálogo' : 'Mostrar en catálogo'}
                        >
                          {cat.activo
                            ? <ToggleRight className="h-8 w-8 text-green-500 mx-auto" />
                            : <ToggleLeft  className="h-8 w-8 text-gray-400 mx-auto" />}
                        </button>
                      ) : (
                        <span className={`text-[11px] font-bold ${cat.activo ? 'text-green-600' : 'text-gray-400'}`}>
                          {cat.activo ? 'Visible' : 'Oculta'}
                        </span>
                      )}
                    </td>

                    {/* Botón Modificar */}
                    {puedeEditar && (
                      <td className="p-3 text-center">
                        {!eliminada && (
                          <button
                            onClick={() => abrirEditar(cat)}
                            title="Editar categoría"
                            className="p-1.5 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                          >
                            <Edit className="h-4 w-4" />
                          </button>
                        )}
                      </td>
                    )}

                    {/* Fechas */}
                    <td className="p-3 text-xs whitespace-nowrap text-gray-500">
                      {fmtFecha(cat.creado_en)}
                    </td>
                    <td className="p-3 text-xs whitespace-nowrap text-gray-500">
                      {fmtFecha(cat.actualizado_en)}
                    </td>

                    {/* Columna Eliminado: toggle on/off */}
                    <td className="p-3 text-center">
                      {eliminada ? (
                        <div className="flex flex-col items-center gap-1">
                          <span className="text-[10px] font-bold text-red-600 whitespace-nowrap">
                            {fmtFecha(cat.eliminado_en)}
                          </span>
                          {puedeEditar && (
                            <button
                              onClick={() => mutReactivar.mutate(cat.id)}
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
                              const tieneHijos = cat.subcategorias?.length > 0;
                              const msg = tieneHijos
                                ? `"${cat.nombre}" tiene ${cat.subcategorias.length} sub-categoría(s).\nEl backend bloqueará la eliminación si tienen productos activos.\n¿Intentar igualmente?`
                                : `¿Eliminar "${cat.nombre}"?\nPodrás reactivarla después.`;
                              if (window.confirm(msg)) {
                                mutEliminar.mutate(cat.id);
                              }
                            }}
                            title="Dar de baja"
                            className="flex items-center gap-1 text-[10px] font-bold px-2 py-1 rounded-lg bg-slate-100 text-slate-500 hover:bg-red-100 hover:text-red-600 transition-colors"
                          >
                            <Trash2 className="h-3 w-3" /> Eliminar
                          </button>
                        ) : (
                          <span className="text-[10px] text-gray-400">Activa</span>
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
            <span className="ml-2 text-slate-400">({filtradas.length} total)</span>
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
        <CategoriaModal
          categoria={categoriaEditando}
          categoriasDisponibles={categorias}
          onClose={() => setIsModalOpen(false)}
          onSave={(payload) => mutGuardar.mutate(payload)}
        />
      )}
    </div>
  );
}
