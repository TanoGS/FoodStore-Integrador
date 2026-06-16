import { useState, useMemo, useRef, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Edit, Trash2, RotateCcw, AlertTriangle, ChevronLeft, ChevronRight, Plus, X, AlertCircle } from 'lucide-react';
import { CatalogoService } from '../../services/catalogo.service';
import IngredienteModal from '../../components/admin/IngredienteModal';
import { useRole } from '../../hooks/useRole';
import { useWSStore, type StockAlerta } from '../../store/wsStore';

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

  // ── WebSocket: suscripción a alertas de stock bajo ─────────────────────────
  const stockAlertas = useWSStore((s) => s.stockAlertas);
  // Alerta visible en el modal (la más reciente que no fue dismissada)
  const [alertaActual, setAlertaActual] = useState<StockAlerta | null>(null);

  // Cuando llega una nueva alerta, mostrarla y hacer refresh de la tabla
  const prevCountRef = useRef(stockAlertas.length);
  useEffect(() => {
    if (stockAlertas.length > prevCountRef.current) {
      const latest = stockAlertas[stockAlertas.length - 1];
      setAlertaActual(latest);
      void invalidar(); // refresh del query de ingredientes
    }
    prevCountRef.current = stockAlertas.length;
  }, [stockAlertas, invalidar]);

  const cerrarAlerta = () => setAlertaActual(null);

  return (
    <div className="bg-slate-800 rounded-2xl border border-slate-700 p-6">

      {/* CABECERA */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
        <div>
          <h2 className="text-xl font-black text-white">Depósito e Insumos</h2>
          <p className="text-slate-400 text-sm mt-0.5">
            {filtrados.length} ingrediente{filtrados.length !== 1 ? 's' : ''} encontrado{filtrados.length !== 1 ? 's' : ''}
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
              <th className="p-3 font-bold">Nombre</th>
              <th className="p-3 font-bold text-right">Stock Actual</th>
              <th className="p-3 font-bold">Unidad de Medida</th>
              <th className="p-3 font-bold text-right">Costo</th>
              <th className="p-3 font-bold text-right">Stock Seguridad</th>
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
                  Cargando depósito...
                </td>
              </tr>
            ) : paginados.length === 0 ? (
              <tr>
                <td colSpan={colSpan} className="p-8 text-center text-slate-500">
                  Sin resultados para "{filtroNombre}".
                </td>
              </tr>
            ) : (
              paginados.map((ing) => {
                const eliminado = ing.eliminado_en !== null;
                const rowCls = eliminado
                  ? 'bg-red-900/20 text-red-300'
                  : 'hover:bg-slate-700/30 text-slate-200';

                return (
                  <tr key={ing.id} className={`transition-colors ${rowCls}`}>

                    {/* Nombre + badge alérgeno */}
                    <td className="p-3 font-bold text-white">
                      {ing.nombre}
                      {ing.es_alergeno && (
                        <span className="ml-2 inline-flex items-center gap-0.5 text-[10px] font-black px-1.5 py-0.5 rounded-full bg-red-900/40 text-red-400 border border-red-700/50">
                          <AlertTriangle className="h-2.5 w-2.5" /> Alér.
                        </span>
                      )}
                    </td>

                    <td className="p-3 text-right font-medium text-white">{ing.stock}</td>
                    <td className="p-3 text-xs text-slate-400">{ing.unidad_medida}</td>
                    <td className={`p-3 text-right font-medium ${eliminado ? 'text-slate-400' : 'text-orange-400'}`}>
                      ${ing.costo_unitario}
                    </td>
                    <td className="p-3 text-right text-slate-400">{ing.stock_seguridad}</td>

                    {puedeEditar && (
                      <td className="p-3 text-center">
                        {!eliminado && (
                          <button
                            onClick={() => abrirEditar(ing)}
                            title="Editar ingrediente"
                            className="p-1.5 text-blue-400 hover:bg-blue-900/30 rounded-lg transition-colors"
                          >
                            <Edit className="h-4 w-4" />
                          </button>
                        )}
                      </td>
                    )}

                    <td className="p-3 text-xs whitespace-nowrap text-slate-400">
                      {fmtFecha(ing.creado_en)}
                    </td>
                    <td className="p-3 text-xs whitespace-nowrap text-slate-400">
                      {fmtFecha(ing.actualizado_en)}
                    </td>

                    <td className="p-3 text-center">
                      {eliminado ? (
                        <div className="flex flex-col items-center gap-1">
                          <span className="text-[10px] font-bold text-red-400 whitespace-nowrap">
                            {fmtFecha(ing.eliminado_en)}
                          </span>
                          {puedeEditar && (
                            <button
                              onClick={() => mutReactivar.mutate(ing.id)}
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
                              if (window.confirm(`¿Eliminar "${ing.nombre}"?\nPodrás reactivarlo después.`)) {
                                mutEliminar.mutate(ing.id);
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

      {/* MODAL de ingrediente */}
      {isModalOpen && (
        <IngredienteModal
          ingrediente={ingredienteEditando}
          onClose={() => setIsModalOpen(false)}
          onSave={(payload) => mutGuardar.mutate(payload)}
        />
      )}

      {/* MODAL de alerta de stock bajo */}
      {alertaActual && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="stock-alerta-title"
        >
          <div className="bg-slate-800 border-2 border-red-500 rounded-2xl shadow-2xl shadow-red-500/20 w-full max-w-md overflow-hidden">
            {/* Header rojo */}
            <div className="bg-red-900/60 px-6 py-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <AlertCircle className="w-6 h-6 text-red-300" />
                <h2 id="stock-alerta-title" className="text-lg font-black text-red-200">
                  ¡Stock Bajo!
                </h2>
              </div>
              <button
                onClick={cerrarAlerta}
                aria-label="Cerrar alerta"
                className="text-red-300 hover:text-red-100 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Contenido */}
            <div className="p-6 space-y-4">
              <div>
                <p className="text-slate-400 text-sm mb-1">Ingrediente</p>
                <p className="text-white font-black text-xl">{alertaActual.ingrediente_nombre}</p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="bg-red-900/30 border border-red-700/40 rounded-xl p-3 text-center">
                  <p className="text-red-400 text-xs font-bold uppercase mb-1">Stock Actual</p>
                  <p className="text-red-200 font-black text-2xl">
                    {alertaActual.stock_actual}
                    <span className="text-sm font-normal text-red-400 ml-1">
                      {alertaActual.unidad_medida}
                    </span>
                  </p>
                </div>
                <div className="bg-slate-700 border border-slate-600 rounded-xl p-3 text-center">
                  <p className="text-slate-400 text-xs font-bold uppercase mb-1">Stock Mínimo</p>
                  <p className="text-slate-200 font-black text-2xl">
                    {alertaActual.stock_seguridad}
                    <span className="text-sm font-normal text-slate-400 ml-1">
                      {alertaActual.unidad_medida}
                    </span>
                  </p>
                </div>
              </div>

              <p className="text-slate-400 text-xs">
                Este ingrediente quedó por debajo del stock de seguridad tras procesar el pedido #{alertaActual.pedido_id}.
                Considerá reponerlo para no afectar futuras ventas.
              </p>
            </div>

            {/* Acciones */}
            <div className="px-6 pb-6 flex gap-3">
              <button
                onClick={cerrarAlerta}
                className="flex-1 bg-slate-700 hover:bg-slate-600 text-slate-200 font-bold py-2.5 rounded-xl transition-colors"
              >
                Entendido
              </button>
              <button
                onClick={() => {
                  cerrarAlerta();
                  // Ir a la fila del ingrediente en la tabla
                  setFiltroNombre(alertaActual.ingrediente_nombre);
                  setPagina(1);
                }}
                className="flex-1 bg-red-700 hover:bg-red-600 text-white font-bold py-2.5 rounded-xl transition-colors"
              >
                Ir al ingrediente
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
