import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { UsuarioService } from '../../services/usuario.service'; // Usaremos el servicio que ya tienes

export default function Register() {
  const [formData, setFormData] = useState({
    nombre: '',
    apellido: '',
    email: '',
    password: '',
    rol: 'CLIENTE' // Forzamos a que todo el que se registre por aquí sea CLIENTE
  });
  
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      // Usamos el mismo servicio que creaste para el panel de Admin
      await UsuarioService.crear(formData);
      
      // Si sale bien, lo mandamos al login para que inicie sesión
      alert('¡Cuenta creada con éxito! Por favor, inicia sesión.');
      navigate('/login');
      
    } catch (err: any) {
      console.error(err);
      if (err.response?.status === 400) {
        setError('El correo electrónico ya está registrado.');
      } else {
        setError('Ocurrió un error al intentar crear la cuenta.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center bg-gray-50 px-4 py-12">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-lg p-8">
        <div className="text-center mb-8">
          <h2 className="text-3xl font-extrabold text-gray-900">Crear Cuenta</h2>
          <p className="text-gray-500 mt-2">Únete a Food Store para hacer tu pedido</p>
        </div>

        {error && (
          <div className="bg-red-50 text-red-600 p-3 rounded-lg text-sm mb-6 text-center border border-red-100">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Nombre</label>
              <input
                type="text"
                required
                value={formData.nombre}
                onChange={(e) => setFormData({...formData, nombre: e.target.value})}
                className="w-full px-4 py-3 rounded-xl border border-gray-300 focus:ring-2 focus:ring-orange-500 focus:border-orange-500 transition-colors"
                placeholder="Juan"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Apellido</label>
              <input
                type="text"
                required
                value={formData.apellido}
                onChange={(e) => setFormData({...formData, apellido: e.target.value})}
                className="w-full px-4 py-3 rounded-xl border border-gray-300 focus:ring-2 focus:ring-orange-500 focus:border-orange-500 transition-colors"
                placeholder="Pérez"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Correo Electrónico</label>
            <input
              type="email"
              required
              value={formData.email}
              onChange={(e) => setFormData({...formData, email: e.target.value})}
              className="w-full px-4 py-3 rounded-xl border border-gray-300 focus:ring-2 focus:ring-orange-500 focus:border-orange-500 transition-colors"
              placeholder="ejemplo@correo.com"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Contraseña</label>
            <input
              type="password"
              required
              minLength={6}
              value={formData.password}
              onChange={(e) => setFormData({...formData, password: e.target.value})}
              className="w-full px-4 py-3 rounded-xl border border-gray-300 focus:ring-2 focus:ring-orange-500 focus:border-orange-500 transition-colors"
              placeholder="••••••••"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-orange-600 hover:bg-orange-700 text-white font-bold py-3 rounded-xl transition-colors disabled:bg-orange-400 flex justify-center items-center mt-2"
          >
            {loading ? (
              <div className="h-5 w-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
            ) : (
              'Registrarme'
            )}
          </button>
        </form>

        {/* Link para volver al login */}
        <div className="mt-8 text-center text-sm text-gray-600">
          ¿Ya tienes una cuenta?{' '}
          <Link to="/login" className="font-bold text-orange-600 hover:text-orange-500 transition-colors">
            Inicia sesión aquí
          </Link>
        </div>
      </div>
    </div>
  );
}