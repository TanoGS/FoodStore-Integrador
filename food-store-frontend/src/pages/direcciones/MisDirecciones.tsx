import { useState, useEffect } from 'react';
import { MapPin, Plus, Star, X, Trash2, Edit2, CheckCircle } from 'lucide-react';
import { DireccionService, type Direccion, type CrearDireccionPayload } from '../../services/direccion.service';
import { useAuthStore } from '../../store/authStore';
import { useNavigate } from 'react-router-dom';

const FORM_VACÍO: CrearDireccionPayload = {
  alias:          '',
  calle:          '',
  numero:         '',
  piso:           '',
  departamento:   '',
  ciudad:         'Mendoza',
  codigo_postal:  '',
  predeterminada: false,
};

export default function MisDirecciones() {
  const [direcciones,   setDirecciones]   = useState<Direccion[]>([]);
  const [modalAbierto,  setModalAbierto]  = useState(false);
  const [editando,      setEditando]      = useState<Direccion | null>(null);
  const [loading,       setLoading]       = useState(false);
  const [errorMsg,      setErrorMsg]      = useState('');
  const [formData,      setFormData]      = useState<CrearDireccionPayload>(FORM_VACÍO);

  const isAuthenticated = useAuthStore(state => state.isAuthenticated);
  const navigate        = useNavigate();

  useEffect(() => {
    if (!isAuthenticated) { navigate('/login'); return; }
    cargar();
  }, [isAuthenticated, navigate]);

  const cargar = async () => {
    try {
      setDirecciones(await DireccionService.listar());
    } catch {
      console.error('Error cargando direcciones');
    }
  };

  const abrirCrear = () => {
    setEditando(null);
    setFormData(FORM_VACÍO);
    setErrorMsg('');
    setModalAbierto(true);
  };

  const abrirEditar = (dir: Direccion) => {
    setEditando(dir);
    setFormData({
      alias:          dir.alias          || '',
      calle:          dir.calle,
      numero:         dir.numero,
      piso:           dir.piso           || '',
      departamento:   dir.departamento   || '',
      ciudad:         dir.ciudad,
      codigo_postal:  dir.codigo_postal,
      predeterminada: dir.predeterminada,
    });
    setErrorMsg('');
    setModalAbierto(true);
  };

  const cerrarModal = () => {
    setModalAbierto(false);
    setEditando(null);
  };

  const set = (key: keyof CrearDireccionPayload, val: string | boolean) =>
    setFormData(prev => ({ ...prev, [key]: val }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErrorMsg('');
    try {
      if (editando) {
        await DireccionService.actualizar(editando.id, formData);
      } else {
        await DireccionService.crear(formData);
      }
      cerrarModal();
      await cargar();
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setErrorMsg(
        Array.isArray(detail)
          ? detail.map((d: any) => d.msg).join(' · ')
          : detail || 'Error al guardar la dirección.'
      );
    } finally {
      setLoading(false);
    }
  };

  const handleEliminar = async (dir: Direccion) => {
    if (!window.confirm(`¿Eliminar la dirección en ${dir.calle} ${dir.numero}?`)) return;
    try {
      await DireccionService.eliminar(dir.id);
      await cargar();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'No se pudo eliminar la dirección.');
    }
  };

  const handleMarcarPredeterminada = async (id: number) => {
    try {
      await DireccionService.marcarPredeterminada(id);
      await cargar();
    } catch {
      alert('Error al marcar como predeterminada.');
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6 mt-8">
      <div className="flex justify-between items-center mb-8 border-b pb-4">
        <div>
          <h2 className="text-3xl font-extrabold text-slate-800 flex items-center gap-2">
            <MapPin className="text-orange-600 w-8 h-8" />
            Mis Direcciones
          </h2>
          <p className="text-slate-500 mt-1">Gestiona tus lugares de entrega</p>
        </div>
        <button
          onClick={abrirCrear}
          className="bg-orange-600 hover:bg-orange-700 text-white px-5 py-2.5 rounded-xl font-bold flex items-center gap-2 transition-colors shadow-sm"
        >
          <Plus className="w-5 h-5" /> Nueva Dirección
        </button>
      </div>

      {/* Lista */}
      {direcciones.length === 0 ? (
        <div className="text-center bg-slate-50 p-12 rounded-2xl border-2 border-dashed border-slate-200">
          <MapPin className="w-16 h-16 text-slate-300 mx-auto mb-4" />
          <h3 className="text-xl font-bold text-slate-700">Aún no tienes direcciones</h3>
          <p className="text-slate-500 mt-2">Agrega tu primer domicilio para recibir tus pedidos.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {direcciones.map(dir => (
            <div
              key={dir.id}
              className={`p-6 rounded-2xl border-2 relative transition-all ${
                dir.predeterminada
                  ? 'border-orange-500 bg-orange-50'
                  : 'border-slate-200 bg-white hover:border-orange-300'
              }`}
            >
              {/* Badge predeterminada */}
              {dir.predeterminada && (
                <span className="absolute -top-3 -right-3 bg-orange-500 text-white p-2 rounded-full shadow-md" title="Dirección predeterminada">
                  <Star className="w-5 h-5 fill-current" />
                </span>
              )}

              {/* Alias + dirección */}
              {dir.alias && (
                <p className="text-xs font-black text-orange-600 uppercase tracking-wider mb-1">{dir.alias}</p>
              )}
              <h3 className="text-xl font-bold text-slate-800">
                {dir.calle} {dir.numero}
              </h3>
              {(dir.piso || dir.departamento) && (
                <p className="text-slate-600 text-sm">
                  {dir.piso && `Piso ${dir.piso}`}{dir.piso && dir.departamento && ' · '}
                  {dir.departamento && `Depto ${dir.departamento}`}
                </p>
              )}
              <p className="text-slate-600 text-sm">{dir.ciudad} · CP {dir.codigo_postal}</p>

              {/* Acciones */}
              <div className="flex items-center gap-2 mt-4 pt-4 border-t border-slate-200/80">
                {!dir.predeterminada && (
                  <button
                    onClick={() => handleMarcarPredeterminada(dir.id)}
                    className="flex items-center gap-1.5 text-xs font-bold text-orange-600 hover:text-orange-700 bg-orange-50 hover:bg-orange-100 px-3 py-1.5 rounded-lg transition"
                  >
                    <CheckCircle className="w-3.5 h-3.5" /> Usar como predeterminada
                  </button>
                )}
                <div className="ml-auto flex gap-2">
                  <button
                    onClick={() => abrirEditar(dir)}
                    className="p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition"
                    title="Editar"
                  >
                    <Edit2 className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleEliminar(dir)}
                    className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition"
                    title="Eliminar"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal Crear / Editar */}
      {modalAbierto && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden">
            <div className="bg-slate-800 p-5 text-white flex justify-between items-center">
              <h3 className="text-lg font-bold">{editando ? 'Editar Dirección' : 'Agregar Domicilio'}</h3>
              <button onClick={cerrarModal} className="text-slate-300 hover:text-white">
                <X className="w-6 h-6" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              {/* Alias */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Alias (Opcional)</label>
                <input type="text" value={formData.alias} onChange={e => set('alias', e.target.value)}
                  placeholder="Ej: Casa, Trabajo..."
                  className="w-full p-2.5 border border-slate-200 rounded-lg focus:ring-2 focus:ring-orange-500 outline-none" />
              </div>

              {/* Calle + Número */}
              <div className="grid grid-cols-3 gap-4">
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-slate-700 mb-1">Calle *</label>
                  <input required type="text" value={formData.calle} onChange={e => set('calle', e.target.value)}
                    className="w-full p-2.5 border border-slate-200 rounded-lg focus:ring-2 focus:ring-orange-500 outline-none" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Número *</label>
                  <input required type="text" value={formData.numero} onChange={e => set('numero', e.target.value)}
                    className="w-full p-2.5 border border-slate-200 rounded-lg focus:ring-2 focus:ring-orange-500 outline-none" />
                </div>
              </div>

              {/* Piso + Depto + Ciudad */}
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Piso (Opc.)</label>
                  <input type="text" value={formData.piso} onChange={e => set('piso', e.target.value)}
                    className="w-full p-2.5 border border-slate-200 rounded-lg focus:ring-2 focus:ring-orange-500 outline-none" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Depto (Opc.)</label>
                  <input type="text" value={formData.departamento} onChange={e => set('departamento', e.target.value)}
                    className="w-full p-2.5 border border-slate-200 rounded-lg focus:ring-2 focus:ring-orange-500 outline-none" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Ciudad *</label>
                  <input required type="text" value={formData.ciudad} onChange={e => set('ciudad', e.target.value)}
                    className="w-full p-2.5 border border-slate-200 rounded-lg focus:ring-2 focus:ring-orange-500 outline-none" />
                </div>
              </div>

              {/* Código Postal */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Código Postal *</label>
                <input required type="text" value={formData.codigo_postal} onChange={e => set('codigo_postal', e.target.value)}
                  placeholder="Ej: 5500"
                  className="w-full p-2.5 border border-slate-200 rounded-lg focus:ring-2 focus:ring-orange-500 outline-none" />
              </div>

              {/* Predeterminada */}
              <div className="flex items-center gap-2 bg-orange-50 p-3 rounded-lg border border-orange-100">
                <input type="checkbox" id="predeterminada" checked={formData.predeterminada}
                  onChange={e => set('predeterminada', e.target.checked)}
                  className="w-5 h-5 accent-orange-600 rounded" />
                <label htmlFor="predeterminada" className="text-sm font-medium text-orange-900 cursor-pointer">
                  Marcar como dirección predeterminada
                </label>
              </div>

              {/* Error */}
              {errorMsg && (
                <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg p-3 font-medium">
                  {errorMsg}
                </p>
              )}

              <div className="flex justify-end gap-3 mt-2 border-t pt-4">
                <button type="button" onClick={cerrarModal}
                  className="px-5 py-2.5 text-slate-600 hover:bg-slate-100 rounded-xl font-medium transition">
                  Cancelar
                </button>
                <button type="submit" disabled={loading}
                  className="bg-orange-600 hover:bg-orange-700 text-white px-6 py-2.5 rounded-xl font-bold transition disabled:opacity-50">
                  {loading ? 'Guardando...' : 'Guardar Dirección'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

