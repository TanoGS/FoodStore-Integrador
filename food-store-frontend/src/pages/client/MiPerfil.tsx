import { useState } from 'react';
import { User, Phone, Mail, Lock, Save, CheckCircle, AlertCircle } from 'lucide-react';
import { useAuthStore } from '../../store/authStore';
import api from '../../config/axios';

export default function MiPerfil() {
  const { user, updateUser } = useAuthStore();

  // ── Datos personales ──────────────────────────────────────────────────────
  const [datos, setDatos] = useState({
    nombre:   user?.nombre   || '',
    apellido: user?.apellido || '',
    cel:      user?.cel      || '',
  });
  const [guardandoDatos,  setGuardandoDatos]  = useState(false);
  const [exitoDatos,      setExitoDatos]      = useState(false);
  const [errorDatos,      setErrorDatos]      = useState('');

  // ── Contraseña ────────────────────────────────────────────────────────────
  const [pass, setPass] = useState({ nueva: '', confirmar: '' });
  const [guardandoPass,  setGuardandoPass]  = useState(false);
  const [exitoPass,      setExitoPass]      = useState(false);
  const [errorPass,      setErrorPass]      = useState('');

  const iniciales =
    `${user?.nombre?.[0] || ''}${user?.apellido?.[0] || ''}`.toUpperCase() || 'U';

  // ── Guardar datos personales ──────────────────────────────────────────────
  const handleGuardarDatos = async (e: React.FormEvent) => {
    e.preventDefault();
    setGuardandoDatos(true);
    setExitoDatos(false);
    setErrorDatos('');
    try {
      const { data } = await api.patch('/usuarios/me', {
        nombre:   datos.nombre.trim(),
        apellido: datos.apellido.trim(),
        cel:      datos.cel.trim() || null,
      });
      updateUser(data);
      setExitoDatos(true);
      setTimeout(() => setExitoDatos(false), 3000);
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setErrorDatos(
        Array.isArray(detail) ? detail.map((d: any) => d.msg).join(' · ') : detail || 'Error al guardar.'
      );
    } finally {
      setGuardandoDatos(false);
    }
  };

  // ── Cambiar contraseña ────────────────────────────────────────────────────
  const handleCambiarPass = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorPass('');
    setExitoPass(false);
    if (pass.nueva !== pass.confirmar) {
      setErrorPass('Las contraseñas no coinciden.');
      return;
    }
    if (pass.nueva.length < 6) {
      setErrorPass('La contraseña debe tener al menos 6 caracteres.');
      return;
    }
    setGuardandoPass(true);
    try {
      await api.patch('/usuarios/me', { password: pass.nueva });
      setPass({ nueva: '', confirmar: '' });
      setExitoPass(true);
      setTimeout(() => setExitoPass(false), 3000);
    } catch (err: any) {
      setErrorPass(err.response?.data?.detail || 'Error al cambiar la contraseña.');
    } finally {
      setGuardandoPass(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-6 mt-8 space-y-8">

      {/* Cabecera – Avatar + info */}
      <div className="flex items-center gap-6 bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
        <div className="w-20 h-20 rounded-full bg-orange-600 flex items-center justify-center text-2xl font-black text-white shrink-0 select-none">
          {iniciales}
        </div>
        <div>
          <h1 className="text-2xl font-black text-slate-900">
            {user?.nombre} {user?.apellido}
          </h1>
          <p className="text-slate-500 mt-0.5 text-sm">{user?.email}</p>
          <div className="flex flex-wrap gap-2 mt-2">
            {user?.roles?.map((r: any) => (
              <span key={r.codigo}
                className="text-[10px] bg-orange-100 text-orange-700 px-2 py-0.5 rounded-full font-black uppercase tracking-wide">
                {r.nombre}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Datos personales */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="bg-slate-50 border-b border-gray-100 px-6 py-4">
          <h2 className="font-black text-slate-800 flex items-center gap-2">
            <User className="w-5 h-5 text-orange-500" />
            Datos Personales
          </h2>
        </div>
        <form onSubmit={handleGuardarDatos} className="p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-bold text-slate-700 mb-1">Nombre *</label>
              <input
                required type="text" value={datos.nombre}
                onChange={e => setDatos(d => ({ ...d, nombre: e.target.value }))}
                className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-orange-500 outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-bold text-slate-700 mb-1">Apellido *</label>
              <input
                required type="text" value={datos.apellido}
                onChange={e => setDatos(d => ({ ...d, apellido: e.target.value }))}
                className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-orange-500 outline-none"
              />
            </div>
            <div className="col-span-2">
              <label className="block text-sm font-bold text-slate-700 mb-1 flex items-center gap-1.5">
                <Phone className="w-3.5 h-3.5" /> Teléfono / Celular
              </label>
              <input
                type="tel" value={datos.cel}
                onChange={e => setDatos(d => ({ ...d, cel: e.target.value }))}
                placeholder="+54 261 555-0000"
                className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-orange-500 outline-none"
              />
            </div>
            <div className="col-span-2">
              <label className="block text-sm font-bold text-slate-700 mb-1 flex items-center gap-1.5">
                <Mail className="w-3.5 h-3.5" /> Email
              </label>
              <input
                disabled type="email" value={user?.email || ''}
                className="w-full px-4 py-2.5 bg-slate-100 border border-slate-200 rounded-xl text-slate-400 cursor-not-allowed"
              />
              <p className="text-xs text-slate-400 mt-1">El email no puede modificarse desde aquí.</p>
            </div>
          </div>

          {errorDatos && (
            <div className="flex items-center gap-2 text-sm text-red-700 bg-red-50 border border-red-200 rounded-xl p-3">
              <AlertCircle className="w-4 h-4 shrink-0" /> {errorDatos}
            </div>
          )}

          <div className="flex justify-end items-center gap-4 pt-2">
            {exitoDatos && (
              <span className="flex items-center gap-1.5 text-green-600 font-bold text-sm">
                <CheckCircle className="w-4 h-4" /> Cambios guardados
              </span>
            )}
            <button
              type="submit" disabled={guardandoDatos}
              className="flex items-center gap-2 bg-orange-600 hover:bg-orange-700 text-white px-6 py-2.5 rounded-xl font-bold transition shadow-sm disabled:opacity-50"
            >
              <Save className="w-4 h-4" />
              {guardandoDatos ? 'Guardando...' : 'Guardar Cambios'}
            </button>
          </div>
        </form>
      </div>

      {/* Cambiar contraseña */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="bg-slate-50 border-b border-gray-100 px-6 py-4">
          <h2 className="font-black text-slate-800 flex items-center gap-2">
            <Lock className="w-5 h-5 text-orange-500" />
            Cambiar Contraseña
          </h2>
        </div>
        <form onSubmit={handleCambiarPass} className="p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-bold text-slate-700 mb-1">Nueva Contraseña *</label>
              <input
                required type="password" value={pass.nueva} minLength={6}
                onChange={e => setPass(p => ({ ...p, nueva: e.target.value }))}
                placeholder="Mínimo 6 caracteres"
                className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-orange-500 outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-bold text-slate-700 mb-1">Confirmar Contraseña *</label>
              <input
                required type="password" value={pass.confirmar}
                onChange={e => setPass(p => ({ ...p, confirmar: e.target.value }))}
                className={`w-full px-4 py-2.5 bg-slate-50 border rounded-xl focus:ring-2 focus:ring-orange-500 outline-none ${
                  errorPass ? 'border-red-400' : 'border-slate-200'
                }`}
              />
            </div>
          </div>

          {errorPass && (
            <div className="flex items-center gap-2 text-sm text-red-700 bg-red-50 border border-red-200 rounded-xl p-3">
              <AlertCircle className="w-4 h-4 shrink-0" /> {errorPass}
            </div>
          )}

          <div className="flex justify-end items-center gap-4 pt-2">
            {exitoPass && (
              <span className="flex items-center gap-1.5 text-green-600 font-bold text-sm">
                <CheckCircle className="w-4 h-4" /> Contraseña actualizada
              </span>
            )}
            <button
              type="submit" disabled={guardandoPass}
              className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-white px-6 py-2.5 rounded-xl font-bold transition shadow-sm disabled:opacity-50"
            >
              <Lock className="w-4 h-4" />
              {guardandoPass ? 'Actualizando...' : 'Cambiar Contraseña'}
            </button>
          </div>
        </form>
      </div>

    </div>
  );
}
