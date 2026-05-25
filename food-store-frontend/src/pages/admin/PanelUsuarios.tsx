import { useState, useEffect } from 'react';
import { Shield, Trash2, RefreshCcw, Plus, X, UserCog } from 'lucide-react';
import { UsuarioService } from '../../services/usuario.service';

// Mapeo de nombres a IDs (según tu script init_db.py)
const ROLE_MAP: Record<string, number> = {
  'ADMIN': 1,
  'CLIENTE': 2,
  'GESTOR_STOCK': 3,
  'GESTOR_PEDIDOS': 4
};

export default function PanelUsuarios() {
  const [usuarios, setUsuarios] = useState<any[]>([]);
  const [modalAbierto, setModalAbierto] = useState(false);
  
  const [formData, setFormData] = useState({
    email: '', 
    nombre: '', 
    apellido: '', 
    password: '', 
    role_ids: [2] // Por defecto ID 2 (CLIENTE)
  });

  const cargarUsuarios = async () => {
    try {
      const res = await UsuarioService.listar();
      // 👇 CORRECCIÓN 1: Si 'res' ya es el arreglo, usamos 'res'. Si viene anidado en Axios, usamos 'res.data'
      const dataLimpia = res.data || res;
      // Nos aseguramos de que siempre sea un arreglo para que el .map() de abajo nunca explote
      setUsuarios(Array.isArray(dataLimpia) ? dataLimpia : []); 
    } catch (error) {
      console.error("Error al cargar usuarios:", error);
    }
  };

  useEffect(() => {
    cargarUsuarios();
  }, []);

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

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-black text-slate-900">Gestión de Usuarios</h1>
          <p className="text-slate-500">Administra accesos y roles del personal</p>
        </div>
        <button 
          onClick={() => setModalAbierto(true)}
          className="flex items-center gap-2 bg-orange-600 text-white px-4 py-2 rounded-xl hover:bg-orange-700 transition-colors"
        >
          <Plus className="w-5 h-5" /> Nuevo Usuario
        </button>
      </div>

      {/* Tabla de Usuarios */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        <table className="w-full text-left">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              <th className="px-6 py-4 text-sm font-bold text-slate-700 uppercase">Usuario</th>
              <th className="px-6 py-4 text-sm font-bold text-slate-700 uppercase">Roles</th>
              <th className="px-6 py-4 text-sm font-bold text-slate-700 uppercase">Estado</th>
              <th className="px-6 py-4 text-sm font-bold text-slate-700 uppercase">Acciones</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {usuarios.map((u) => (
              <tr key={u.id} className="hover:bg-slate-50/50 transition-colors">
                <td className="px-6 py-4">
                  <div className="flex flex-col">
                    <span className="font-bold text-slate-900">{u.nombre} {u.apellido}</span>
                    <span className="text-xs text-slate-500">{u.email}</span>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <div className="flex flex-wrap gap-1">
                    {/* 👇 CORRECCIÓN 2: Leemos roles_enlaces y la propiedad rol_codigo */}
                    {(u.roles_enlaces || u.roles || []).map((r: any, idx: number) => {
                      const nombreDelRol = r.rol_codigo || r.nombre || 'DESCONOCIDO';
                      return (
                        <span key={idx} className="px-2 py-0.5 bg-orange-100 text-orange-700 text-[10px] font-black rounded-full uppercase">
                          {nombreDelRol.replace('_', ' ')}
                        </span>
                      );
                    })}
                  </div>
                </td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-1 rounded-lg text-xs font-bold ${u.activo ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                    {u.activo ? 'ACTIVO' : 'INACTIVO'}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <div className="flex gap-2">
                    <button className="p-2 text-slate-400 hover:text-orange-600 transition-colors"><UserCog className="w-5 h-5" /></button>
                    <button className="p-2 text-slate-400 hover:text-red-600 transition-colors"><Trash2 className="w-5 h-5" /></button>
                  </div>
                </td>
              </tr>
            ))}
            {usuarios.length === 0 && (
              <tr>
                <td colSpan={4} className="p-8 text-center text-slate-500">
                  No se encontraron usuarios o cargando...
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* MODAL */}
      {modalAbierto && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-3xl w-full max-w-md shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-200">
            <div className="bg-slate-900 p-6 text-white flex justify-between items-center">
              <h2 className="text-xl font-black">Crear Nuevo Usuario</h2>
              <button onClick={() => setModalAbierto(false)} className="hover:text-red-400 transition-colors"><X /></button>
            </div>
            
            <form onSubmit={handleCrear} className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1 text-slate-700">Nombre</label>
                  <input required value={formData.nombre} onChange={e => setFormData({...formData, nombre: e.target.value})} className="w-full px-4 py-2 border border-slate-300 rounded-xl outline-none focus:ring-2 focus:ring-orange-500" />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1 text-slate-700">Apellido</label>
                  <input required value={formData.apellido} onChange={e => setFormData({...formData, apellido: e.target.value})} className="w-full px-4 py-2 border border-slate-300 rounded-xl outline-none focus:ring-2 focus:ring-orange-500" />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1 text-slate-700">Email</label>
                <input required type="email" value={formData.email} onChange={e => setFormData({...formData, email: e.target.value})} className="w-full px-4 py-2 border border-slate-300 rounded-xl outline-none focus:ring-2 focus:ring-orange-500" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1 text-slate-700">Contraseña</label>
                <input required type="password" value={formData.password} onChange={e => setFormData({...formData, password: e.target.value})} className="w-full px-4 py-2 border border-slate-300 rounded-xl outline-none focus:ring-2 focus:ring-orange-500" />
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-1 text-slate-700">Rol Principal</label>
                <select 
                  value={Object.keys(ROLE_MAP).find(key => ROLE_MAP[key] === formData.role_ids[0])} 
                  onChange={e => setFormData({...formData, role_ids: [ROLE_MAP[e.target.value]]})} 
                  className="w-full px-4 py-2 border border-slate-300 rounded-xl bg-white outline-none focus:ring-2 focus:ring-orange-500"
                >
                  <option value="CLIENTE">Cliente</option>
                  <option value="GESTOR_STOCK">Gestor de Stock</option>
                  <option value="GESTOR_PEDIDOS">Gestor de Pedidos</option>
                  <option value="ADMIN">Administrador</option>
                </select>
              </div>

              <div className="flex justify-end gap-3 mt-6">
                <button type="button" onClick={() => setModalAbierto(false)} className="px-5 py-2.5 text-slate-600 font-bold hover:bg-slate-50 rounded-xl transition-colors">Cancelar</button>
                <button type="submit" className="px-5 py-2.5 bg-orange-600 text-white rounded-xl font-bold hover:bg-orange-700 transition-colors shadow-lg shadow-orange-600/20">Crear Cuenta</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}