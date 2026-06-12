import { useState, useEffect, useMemo } from 'react';
import { Trash2, Plus, X, UserCog, RotateCcw, ChevronLeft, ChevronRight } from 'lucide-react';
import { UsuarioService } from '../../services/usuario.service';

const ITEMS_POR_PAGINA = 10;

// Mapeo de nombres a IDs
const ROLE_MAP: Record<string, number> = {
  'ADMIN': 1,
  'CLIENTE': 2,
  'GESTOR_STOCK': 3,
  'GESTOR_PEDIDOS': 4,
  'CAJERO': 5,
  'COCINA': 6
};

type FiltroRol = 'TODOS' | 'CLIENTES' | 'STAFF';

// Colores por rol (case-insensitive con toUpperCase)
const ROLE_COLORS: Record<string, string> = {
  'ADMIN': 'bg-purple-900/60 text-purple-300 border border-purple-700/50',
  'GESTOR_STOCK': 'bg-blue-900/60 text-blue-300 border border-blue-700/50',
  'GESTOR_PEDIDOS': 'bg-cyan-900/60 text-cyan-300 border border-cyan-700/50',
  'CAJERO': 'bg-yellow-900/60 text-yellow-300 border border-yellow-700/50',
  'COCINA': 'bg-orange-900/60 text-orange-300 border border-orange-700/50',
  'CLIENTE': 'bg-green-900/60 text-green-300 border border-green-700/50',
};

const getRolColor = (codigo: string) => {
  const key = (codigo || '').toUpperCase();
  return ROLE_COLORS[key] || 'bg-slate-700 text-slate-300 border border-slate-600';
};

const getRolCodigo = (r: any) => (r.rol_codigo || r.codigo || r.nombre || 'CLIENTE').toUpperCase();

const isCliente = (u: any) =>
  (u.roles || []).some((r: any) => getRolCodigo(r) === 'CLIENTE');

const isStaff = (u: any) =>
  (u.roles || []).some((r: any) => getRolCodigo(r) !== 'CLIENTE');

export default function PanelUsuarios() {
  const [usuarios, setUsuarios] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [filtro, setFiltro] = useState<FiltroRol>('TODOS');
  const [pagina, setPagina] = useState(1);

  const [modalAbierto, setModalAbierto] = useState(false);
  const [usuarioEditando, setUsuarioEditando] = useState<any | null>(null);

  const [formData, setFormData] = useState({
    email: '',
    nombre: '',
    apellido: '',
    password: '',
    role_ids: [2]
  });

  // ── Cargar usuarios ─────────────────────────────────────────────────────────
  const cargarUsuarios = async () => {
    try {
      setLoading(true);
      const data = await UsuarioService.listar();
      setUsuarios(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("Error al cargar usuarios:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { cargarUsuarios(); }, []);

  // ── Filtrado ──────────────────────────────────────────────────────────────
  const filtrados = useMemo(() => {
    if (filtro === 'CLIENTES') return usuarios.filter(isCliente);
    if (filtro === 'STAFF') return usuarios.filter(isStaff);
    return usuarios;
  }, [usuarios, filtro]);

  const totalPaginas = Math.max(1, Math.ceil(filtrados.length / ITEMS_POR_PAGINA));
  const paginaActual = Math.min(pagina, totalPaginas);
  const paginados = filtrados.slice(
    (paginaActual - 1) * ITEMS_POR_PAGINA,
    paginaActual * ITEMS_POR_PAGINA
  );

  // ── Handlers ──────────────────────────────────────────────────────────────
  const handleFiltro = (v: FiltroRol) => { setFiltro(v); setPagina(1); };

  const abrirNuevo = () => {
    setUsuarioEditando(null);
    setFormData({ email: '', nombre: '', apellido: '', password: '', role_ids: [2] });
    setModalAbierto(true);
  };

  const abrirEditar = (u: any) => {
    setUsuarioEditando(u);
    setFormData({
      email: u.email || '',
      nombre: u.nombre || '',
      apellido: u.apellido || '',
      password: '',
      role_ids: [u.roles_enlaces?.[0]?.id_rol || u.roles?.[0]?.id || 2]
    });
    setModalAbierto(true);
  };

  const handleCrear = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await UsuarioService.crear(formData);
      alert("Usuario creado con éxito");
      setModalAbierto(false);
      setFormData({ email: '', nombre: '', apellido: '', password: '', role_ids: [2] });
      cargarUsuarios();
    } catch (error) {
      console.error(error);
      alert("Error al crear el usuario.");
    }
  };

  const handleActualizar = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!usuarioEditando) return;
    try {
      await UsuarioService.actualizar(usuarioEditando.id, formData);
      alert("Usuario actualizado con éxito");
      setModalAbierto(false);
      setUsuarioEditando(null);
      cargarUsuarios();
    } catch (error) {
      console.error(error);
      alert("Error al actualizar el usuario.");
    }
  };

  const handleEliminar = async (u: any) => {
    if (!window.confirm(`¿Eliminar a "${u.nombre} ${u.apellido}"?\nPodrás reactivarlo después.`)) return;
    try {
      await UsuarioService.eliminar(u.id);
      cargarUsuarios();
    } catch (error) {
      alert("Error al eliminar el usuario.");
    }
  };

  const handleReactivar = async (u: any) => {
    try {
      await UsuarioService.reactivar(u.id);
      cargarUsuarios();
    } catch (error) {
      alert("Error al reactivar el usuario.");
    }
  };

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="p-8 bg-slate-900 min-h-screen">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-black text-white">Gestión de Usuarios</h1>
          <p className="text-slate-400 mt-1">
            {filtrados.length} usuario{filtrados.length !== 1 ? 's' : ''}
          </p>
        </div>
        <button
          onClick={abrirNuevo}
          className="flex items-center gap-2 bg-orange-600 text-white px-4 py-2 rounded-xl hover:bg-orange-500 transition-colors"
        >
          <Plus className="w-5 h-5" /> Nuevo Usuario
        </button>
      </div>

      {/* Tabs de filtro */}
      <div className="flex gap-2 mb-6">
        {(['TODOS', 'CLIENTES', 'STAFF'] as const).map((f) => (
          <button
            key={f}
            onClick={() => handleFiltro(f)}
            className={`px-4 py-2 rounded-lg font-bold text-sm transition-all ${
              filtro === f
                ? 'bg-orange-600 text-white shadow-md'
                : 'bg-slate-800 text-slate-400 border border-slate-700 hover:bg-slate-700 hover:text-white'
            }`}
          >
            {f === 'TODOS' ? 'Todos' : f === 'CLIENTES' ? 'Clientes' : 'Staff del Sistema'}
          </button>
        ))}
      </div>

      {/* Tabla */}
      <div className="bg-slate-800 rounded-2xl border border-slate-700 overflow-hidden">
        <table className="w-full text-left">
          <thead className="bg-slate-900/80 border-b border-slate-700">
            <tr>
              <th className="px-6 py-4 text-xs font-bold text-slate-400 uppercase tracking-wider">Usuario</th>
              <th className="px-6 py-4 text-xs font-bold text-slate-400 uppercase tracking-wider">Roles</th>
              <th className="px-6 py-4 text-xs font-bold text-slate-400 uppercase tracking-wider text-center">Estado</th>
              <th className="px-6 py-4 text-xs font-bold text-slate-400 uppercase tracking-wider text-center">Acciones</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700">
            {loading ? (
              <tr>
                <td colSpan={4} className="p-8 text-center text-slate-400">
                  Cargando...
                </td>
              </tr>
            ) : paginados.length === 0 ? (
              <tr>
                <td colSpan={4} className="p-8 text-center text-slate-500">
                  No hay usuarios en esta categoría.
                </td>
              </tr>
            ) : paginados.map((u) => {
              const eliminado = u.eliminado_en != null;
              return (
                <tr key={u.id} className={`hover:bg-slate-700/30 transition-colors ${eliminado ? 'opacity-60' : ''}`}>
                  <td className="px-6 py-4">
                    <div className="flex flex-col">
                      <span className="font-bold text-white">{u.nombre} {u.apellido}</span>
                      <span className="text-xs text-slate-400">{u.email}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex flex-wrap gap-1">
                      {(u.roles || []).map((r: any, idx: number) => {
                        const codigo = getRolCodigo(r);
                        return (
                          <span key={idx} className={`px-2 py-0.5 text-[10px] font-black rounded-full uppercase ${getRolColor(codigo)}`}>
                            {codigo.replace('_', ' ')}
                          </span>
                        );
                      })}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-center">
                    {eliminado ? (
                      <span className="bg-red-900/60 text-red-300 border border-red-700/50 px-2 py-1 rounded-lg text-xs font-bold">
                        ELIMINADO
                      </span>
                    ) : (
                      <span className={`px-2 py-1 rounded-lg text-xs font-bold ${
                        u.activo
                          ? 'bg-green-900/60 text-green-300 border border-green-700/50'
                          : 'bg-slate-700 text-slate-400 border border-slate-600'
                      }`}>
                        {u.activo ? 'ACTIVO' : 'INACTIVO'}
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center justify-center gap-2">
                      {eliminado ? (
                        <button
                          onClick={() => handleReactivar(u)}
                          className="flex items-center gap-1 px-3 py-1.5 bg-green-900/40 text-green-400 border border-green-700/50 rounded-lg text-xs font-bold hover:bg-green-900/60 transition-colors"
                        >
                          <RotateCcw className="w-3 h-3" /> Reactivar
                        </button>
                      ) : (
                        <>
                          <button
                            onClick={() => abrirEditar(u)}
                            className="p-2 text-blue-400 hover:bg-blue-900/30 rounded-lg transition-colors"
                            title="Editar usuario"
                          >
                            <UserCog className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleEliminar(u)}
                            className="p-2 text-red-400 hover:bg-red-900/30 rounded-lg transition-colors"
                            title="Eliminar usuario"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Paginación */}
      {totalPaginas > 1 && (
        <div className="flex items-center justify-between mt-4">
          <span className="text-sm text-slate-400">
            Página {paginaActual} de {totalPaginas}
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setPagina(p => Math.max(1, p - 1))}
              disabled={paginaActual === 1}
              className="p-2 rounded-lg border border-slate-600 text-slate-400 hover:bg-slate-700 disabled:opacity-40"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              onClick={() => setPagina(p => Math.min(totalPaginas, p + 1))}
              disabled={paginaActual === totalPaginas}
              className="p-2 rounded-lg border border-slate-600 text-slate-400 hover:bg-slate-700 disabled:opacity-40"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* MODAL */}
      {modalAbierto && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-slate-800 rounded-2xl w-full max-w-md shadow-2xl overflow-hidden border border-slate-700">
            <div className="bg-slate-700 p-5 text-white flex justify-between items-center">
              <h2 className="text-lg font-black">
                {usuarioEditando ? 'Editar Usuario' : 'Nuevo Usuario'}
              </h2>
              <button onClick={() => { setModalAbierto(false); setUsuarioEditando(null); }} className="text-slate-400 hover:text-red-400">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={usuarioEditando ? handleActualizar : handleCrear} className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-slate-400 uppercase mb-2">Nombre</label>
                  <input
                    required
                    value={formData.nombre}
                    onChange={e => setFormData({...formData, nombre: e.target.value})}
                    className="w-full px-4 py-3 border border-slate-600 rounded-xl bg-slate-700 text-white outline-none focus:ring-2 focus:ring-orange-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-400 uppercase mb-2">Apellido</label>
                  <input
                    required
                    value={formData.apellido}
                    onChange={e => setFormData({...formData, apellido: e.target.value})}
                    className="w-full px-4 py-3 border border-slate-600 rounded-xl bg-slate-700 text-white outline-none focus:ring-2 focus:ring-orange-500"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-400 uppercase mb-2">Email</label>
                <input
                  required type="email"
                  value={formData.email}
                  onChange={e => setFormData({...formData, email: e.target.value})}
                  className="w-full px-4 py-3 border border-slate-600 rounded-xl bg-slate-700 text-white outline-none focus:ring-2 focus:ring-orange-500"
                />
              </div>
              {!usuarioEditando && (
                <div>
                  <label className="block text-xs font-bold text-slate-400 uppercase mb-2">Contraseña</label>
                  <input
                    required type="password"
                    value={formData.password}
                    onChange={e => setFormData({...formData, password: e.target.value})}
                    className="w-full px-4 py-3 border border-slate-600 rounded-xl bg-slate-700 text-white outline-none focus:ring-2 focus:ring-orange-500"
                  />
                </div>
              )}
              <div>
                <label className="block text-xs font-bold text-slate-400 uppercase mb-2">Rol</label>
                <select
                  value={Object.keys(ROLE_MAP).find(k => ROLE_MAP[k] === formData.role_ids[0]) || 'CLIENTE'}
                  onChange={e => setFormData({...formData, role_ids: [ROLE_MAP[e.target.value]]})}
                  className="w-full px-4 py-3 border border-slate-600 rounded-xl bg-slate-700 text-white outline-none focus:ring-2 focus:ring-orange-500"
                >
                  <option value="CLIENTE">Cliente</option>
                  <option value="GESTOR_STOCK">Gestor de Stock</option>
                  <option value="GESTOR_PEDIDOS">Gestor de Pedidos</option>
                  <option value="CAJERO">Cajero</option>
                  <option value="COCINA">Cocina</option>
                  <option value="ADMIN">Administrador</option>
                </select>
              </div>

              <div className="flex justify-end gap-3 mt-6">
                <button type="button" onClick={() => { setModalAbierto(false); setUsuarioEditando(null); }} className="px-5 py-2.5 text-slate-400 font-bold hover:bg-slate-700 rounded-xl">Cancelar</button>
                <button type="submit" className="px-5 py-2.5 bg-orange-600 text-white rounded-xl font-bold hover:bg-orange-500">
                  {usuarioEditando ? 'Guardar Cambios' : 'Crear Usuario'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}