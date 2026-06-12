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
    <div className="bg-slate-800 rounded-2xl border border-slate-700 p-6">

      {/* CABECERA */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
        <div>
          <h2 className="text-xl font-black text-white">Categorías</h2>
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
            className="border border-slate-600 rounded-xl px-4 py-2 text-sm bg-slate-700 text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-orange-500 w-full sm:w-60"
          />
          {puedeEditar && (
            <button
              onClick={abrirNuevo}
              className="flex items-center gap-1.5 bg-orange-600 hover:bg-orange-500 text-white px-4 py-2 rounded-xl font-bold text-sm transition-colors whitespace-nowrap"
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
            <tr className="bg-slate-900/80 text-slate-400 text-xs uppercase tracking-wider border-b border-slate-700">
              <th className="p-3 font-bold">Nombre</th>
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
                  Cargando categorías...
                </td>
              </tr>
            ) : paginadas.length === 0 ? (
              <tr>
                <td colSpan={colSpan} className="p-8 text-center text-slate-500">
                  Sin resultados para "{filtroNombre}".
                </td>
              </tr>
            ) : (
              paginadas.map((cat) => {
                const eliminada = cat.eliminado_en !== null;
                const rowCls = eliminada
                  ? 'bg-red-900/20 text-red-300'
                  : 'hover:bg-slate-700/30 text-slate-200';

                return (
                  <tr key={cat.id} className={`transition-colors ${rowCls}`}>

                    {/* Nombre + subcategorías */}
                    <td className="p-3">
                      <span className="font-bold text-white">{cat.nombre}</span>
                      {cat.parent_id && (
                        <span className="ml-2 text-[10px] text-slate-500 italic">sub-categoría</span>
                      )}
                      {cat.subcategorias?.length > 0 && (
                        <div className="flex items-center gap-1 text-[11px] text-blue-400 mt-0.5">
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
                            ? <ToggleRight className="h-8 w-8 text-green-400 mx-auto" />
                            : <ToggleLeft  className="h-8 w-8 text-slate-500 mx-auto" />}
                        </button>
                      ) : (
                        <span className={`text-[11px] font-bold ${cat.activo ? 'text-green-400' : 'text-slate-500'}`}>
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
                            className="p-1.5 text-blue-400 hover:bg-blue-900/30 rounded-lg transition-colors"
                          >
                            <Edit className="h-4 w-4" />
                          </button>
                        )}
                      </td>
                    )}

                    {/* Fechas */}
                    <td className="p-3 text-xs whitespace-nowrap text-slate-400">
                      {fmtFecha(cat.creado_en)}
                    </td>
                    <td className="p-3 text-xs whitespace-nowrap text-slate-400">
                      {fmtFecha(cat.actualizado_en)}
                    </td>

                    {/* Columna Eliminado: toggle on/off */}
                    <td className="p-3 text-center">
                      {eliminada ? (
                        <div className="flex flex-col items-center gap-1">
                          <span className="text-[10px] font-bold text-red-400 whitespace-nowrap">
                            {fmtFecha(cat.eliminado_en)}
                          </span>
                          {puedeEditar && (
                            <button
                              onClick={() => mutReactivar.mutate(cat.id)}
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
                              const tieneHijos = cat.subcategorias?.length > 0;
                              const msg = tieneHijos
                                ? `"${cat.nombre}" tiene ${cat.subcategorias.length} sub-categoría(s).\nEl backend bloqueará la eliminación si tienen productos activos.\n¿Intentar igualmente?`
                                : `¿Eliminar "${cat.nombre}"?\nPodrás reactivarla después.`;
                              if (window.confirm(msg)) {
                                mutEliminar.mutate(cat.id);
                              }
                            }}
                            title="Dar de baja"
                            className="flex items-center gap-1 text-[10px] font-bold px-2 py-1 rounded-lg bg-slate-700 text-slate-400 hover:bg-red-900/40 hover:text-red-400 transition-colors"
                          >
                            <Trash2 className="h-3 w-3" /> Eliminar
                          </button>
                        ) : (
                          <span className="text-[10px] text-slate-500">Activa</span>
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
            <span className="ml-2 text-slate-500">({filtradas.length} total)</span>
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
