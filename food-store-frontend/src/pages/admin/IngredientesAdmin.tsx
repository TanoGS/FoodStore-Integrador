import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Edit, Trash2, RotateCcw, AlertTriangle, ChevronLeft, ChevronRight, Plus } from 'lucide-react';
import { CatalogoService } from '../../services/catalogo.service';
import IngredienteModal from '../../components/admin/IngredienteModal';
import { useRole } from '../../hooks/useRole';

// ── TypeScript: interfaz fiel al schema del backend (IngredientePublic) ────────
interface Ingrediente {
  id:              number;
  nombre:          string;
  stock:           number;
  stock_seguridad: number;
  unidad_medida:   string;
  es_alergeno:     boolean;
  costo_unitario:  number;
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

export default function IngredientesAdmin() {
  const queryClient = useQueryClient();
  const { puedeEditar } = useRole();

  const [filtroNombre, setFiltroNombre] = useState('');
  const [pagina, setPagina]             = useState(1);
  const [isModalOpen, setIsModalOpen]   = useState(false);
  const [ingredienteEditando, setIngredienteEditando] = useState<Ingrediente | null>(null);

  // ── SERVER STATE: listado completo (activos + eliminados) ──────────────────
  const { data: ingredientes = [], isLoading } = useQuery<Ingrediente[]>({
    queryKey: ['ingredientes'],
    queryFn:  CatalogoService.getIngredientesTodos,
  });

  // ── FILTRADO + PAGINACIÓN (client-side) ────────────────────────────────────
  const filtrados = useMemo(() => {
    const lower = filtroNombre.toLowerCase().trim();
    return lower
      ? ingredientes.filter(i => i.nombre.toLowerCase().includes(lower))
      : ingredientes;
  }, [ingredientes, filtroNombre]);

  const totalPaginas = Math.max(1, Math.ceil(filtrados.length / ITEMS_POR_PAGINA));
  const paginaActual = Math.min(pagina, totalPaginas);
  const paginados    = filtrados.slice(
    (paginaActual - 1) * ITEMS_POR_PAGINA,
    paginaActual * ITEMS_POR_PAGINA,
  );

  // ── MUTATIONS ──────────────────────────────────────────────────────────────
  const invalidar = () => queryClient.invalidateQueries({ queryKey: ['ingredientes'] });

  const mutGuardar = useMutation({
    mutationFn: (payload: any) =>
      ingredienteEditando
        ? CatalogoService.actualizarIngrediente(ingredienteEditando.id, payload)
        : CatalogoService.crearIngrediente(payload),
    onSuccess: () => { invalidar(); setIsModalOpen(false); },
    onError: (e: any) =>
      alert(`Error: ${e.response?.data?.detail || 'No se pudo guardar'}`),
  });

  const mutEliminar = useMutation({
    mutationFn: (id: number) => CatalogoService.eliminarIngrediente(id),
    onSuccess: invalidar,
    onError: () => alert('No se pudo eliminar el ingrediente.'),
  });

  const mutReactivar = useMutation({
    mutationFn: (id: number) => CatalogoService.reactivarIngrediente(id),
    onSuccess: invalidar,
    onError: () => alert('No se pudo reactivar el ingrediente.'),
  });

  // ── Helpers de UI ──────────────────────────────────────────────────────────
  const handleFiltro = (v: string) => { setFiltroNombre(v); setPagina(1); };
  const abrirEditar  = (ing: Ingrediente) => { setIngredienteEditando(ing); setIsModalOpen(true); };
  const abrirNuevo   = () => { setIngredienteEditando(null); setIsModalOpen(true); };

  const colSpan = puedeEditar ? 9 : 8;

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

      {/* CABECERA */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
        <div>
          <h2 className="text-xl font-black text-slate-800">Depósito e Insumos</h2>
          <p className="text-slate-400 text-sm mt-0.5">
            {filtrados.length} ingrediente{filtrados.length !== 1 ? 's' : ''} encontrado{filtrados.length !== 1 ? 's' : ''}
          </p>
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          {/* Filtro por nombre */}
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
              <th className="p-3 font-semibold text-right">Stock Actual</th>
              <th className="p-3 font-semibold">Unidad de Medida</th>
              <th className="p-3 font-semibold text-right">Costo</th>
              <th className="p-3 font-semibold text-right">Stock Seguridad</th>
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
                  Cargando depósito...
                </td>
              </tr>
            ) : paginados.length === 0 ? (
              <tr>
                <td colSpan={colSpan} className="p-8 text-center text-gray-400">
                  Sin resultados para "{filtroNombre}".
                </td>
              </tr>
            ) : (
              paginados.map((ing) => {
                const eliminado = ing.eliminado_en !== null;
                const rowCls = eliminado
                  ? 'bg-red-50 text-red-800'
                  : 'hover:bg-gray-50 text-gray-800';

                return (
                  <tr key={ing.id} className={`transition-colors ${rowCls}`}>

                    {/* Nombre + badge alérgeno */}
                    <td className="p-3 font-bold">
                      {ing.nombre}
                      {ing.es_alergeno && (
                        <span className="ml-2 inline-flex items-center gap-0.5 text-[10px] font-black px-1.5 py-0.5 rounded-full bg-red-100 text-red-700">
                          <AlertTriangle className="h-2.5 w-2.5" /> Alér.
                        </span>
                      )}
                    </td>

                    <td className="p-3 text-right font-medium">{ing.stock}</td>
                    <td className="p-3 text-xs">{ing.unidad_medida}</td>
                    <td className={`p-3 text-right font-medium ${eliminado ? '' : 'text-orange-600'}`}>
                      ${ing.costo_unitario}
                    </td>
                    <td className="p-3 text-right">{ing.stock_seguridad}</td>

                    {/* Botón Modificar (solo roles con permiso + no eliminado) */}
                    {puedeEditar && (
                      <td className="p-3 text-center">
                        {!eliminado && (
                          <button
                            onClick={() => abrirEditar(ing)}
                            title="Editar ingrediente"
                            className="p-1.5 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                          >
                            <Edit className="h-4 w-4" />
                          </button>
                        )}
                      </td>
                    )}

                    {/* Fechas */}
                    <td className="p-3 text-xs whitespace-nowrap text-gray-500">
                      {fmtFecha(ing.creado_en)}
                    </td>
                    <td className="p-3 text-xs whitespace-nowrap text-gray-500">
                      {fmtFecha(ing.actualizado_en)}
                    </td>

                    {/* Columna Eliminado: toggle on/off */}
                    <td className="p-3 text-center">
                      {eliminado ? (
                        <div className="flex flex-col items-center gap-1">
                          <span className="text-[10px] font-bold text-red-600 whitespace-nowrap">
                            {fmtFecha(ing.eliminado_en)}
                          </span>
                          {puedeEditar && (
                            <button
                              onClick={() => mutReactivar.mutate(ing.id)}
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
                              if (window.confirm(`¿Eliminar "${ing.nombre}"?\nPodrás reactivarlo después.`)) {
                                mutEliminar.mutate(ing.id);
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
        <IngredienteModal
          ingrediente={ingredienteEditando}
          onClose={() => setIsModalOpen(false)}
          onSave={(payload) => mutGuardar.mutate(payload)}
        />
      )}
    </div>
  );
}
