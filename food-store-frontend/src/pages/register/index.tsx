import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { axiosClient } from '../../api/axios';

export const RegisterPage = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    nombre: '',
    apellido: '',
    email: '',
    password: '',
    telefono: ''
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      // Hacemos el POST al backend real
      await axiosClient.post('/usuarios/registro', formData);
      
      // Si sale bien, lo mandamos al login para que inicie sesión
      alert('¡Cuenta creada con éxito! Por favor, inicia sesión.');
      navigate('/login');
    } catch (err: any) {
      // Mostramos el error del backend (ej: "El correo ya está registrado")
      setError(err.response?.data?.detail || 'Ocurrió un error al registrarse');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100 py-12 px-4 sm:px-6 lg:px-8">
      <div className="bg-white p-8 rounded-lg shadow-lg max-w-md w-full">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-orange-600 mb-2">Crear Cuenta</h1>
          <p className="text-gray-500">Únete a Food Store para realizar tus pedidos</p>
        </div>

        {error && (
          <div className="bg-red-50 text-red-600 p-3 rounded-md mb-4 text-sm text-center">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Nombre</label>
              <input type="text" name="nombre" required value={formData.nombre} onChange={handleChange}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-orange-500 focus:border-orange-500 outline-none transition-colors" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Apellido</label>
              <input type="text" name="apellido" required value={formData.apellido} onChange={handleChange}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-orange-500 focus:border-orange-500 outline-none transition-colors" />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Correo Electrónico</label>
            <input type="email" name="email" required value={formData.email} onChange={handleChange}
              className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-orange-500 focus:border-orange-500 outline-none transition-colors" />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Teléfono (Opcional)</label>
            <input type="tel" name="telefono" value={formData.telefono} onChange={handleChange}
              className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-orange-500 focus:border-orange-500 outline-none transition-colors" />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Contraseña</label>
            <input type="password" name="password" required value={formData.password} onChange={handleChange}
              className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-orange-500 focus:border-orange-500 outline-none transition-colors" />
          </div>

          <button type="submit" disabled={loading}
            className="w-full bg-orange-600 text-white font-bold py-2 px-4 rounded-md hover:bg-orange-700 transition-colors focus:ring-4 focus:ring-orange-300 disabled:bg-orange-400">
            {loading ? 'Registrando...' : 'Registrarme'}
          </button>
        </form>

        <div className="mt-6 text-center text-sm text-gray-500">
          ¿Ya tienes una cuenta?{' '}
          <Link to="/login" className="text-orange-600 hover:text-orange-500 font-bold">
            Inicia sesión aquí
          </Link>
        </div>
      </div>
    </div>
  );
};