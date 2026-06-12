import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react';

interface CategoriaModalProps {
  categoria?: any | null;
  onClose: () => void;
  onSave: (payload: any) => void;
  categoriasDisponibles: any[]; 
}

export default function CategoriaModal({ categoria, onClose, onSave, categoriasDisponibles }: CategoriaModalProps) {
  const [nombre, setNombre] = useState('');
  const [descripcion, setDescripcion] = useState('');
  const [parentId, setParentId] = useState<number | ''>('');
  const [activo, setActivo] = useState(true);

  // Si nos pasan una categoría para editar, rellenamos los campos
  useEffect(() => {
    if (categoria) {
      setNombre(categoria.nombre || '');
      setDescripcion(categoria.descripcion || '');
      setParentId(categoria.parent_id || '');
      setActivo(categoria.activo !== false);
    }
  }, [categoria]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave({
      nombre,
      descripcion,
      activo,
      parent_id: parentId === '' ? null : parentId, // Convertimos el string vacío a null para FastAPI
    });
  };

  // Filtramos para que una categoría no pueda ser "hija" de sí misma en la edición
  const opcionesPadre = categoriasDisponibles.filter(c => c.id !== categoria?.id);

  return (
    <div className="fixed inset-0 bg-slate-900/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-slate-800 rounded-2xl shadow-2xl w-full max-w-md overflow-hidden border border-slate-700">
        
        {/* Cabecera */}
        <div className="px-6 py-4 border-b border-slate-700 flex justify-between items-center bg-slate-700">
          <h3 className="font-bold text-lg text-white">
            {categoria ? 'Editar Categoría' : 'Nueva Categoría'}
          </h3>
          <button onClick={onClose} className="text-slate-400 hover:text-red-400 transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Formulario */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          
          <div>
            <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Nombre de la Categoría *</label>
            <input
              type="text"
              required
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
              className="w-full px-4 py-3 rounded-xl border border-slate-600 bg-slate-700 text-white focus:ring-2 focus:ring-orange-500 outline-none placeholder-slate-400"
              placeholder="Ej: Hamburguesas"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Categoría Padre (Opcional)</label>
            <select
              value={parentId}
              onChange={(e) => setParentId(e.target.value === '' ? '' : Number(e.target.value))}
              className="w-full px-4 py-3 rounded-xl border border-slate-600 bg-slate-700 text-white focus:ring-2 focus:ring-orange-500 outline-none"
            >
              <option value="">Ninguna (Es Categoría Principal)</option>
              {opcionesPadre.map((cat) => (
                <option key={cat.id} value={cat.id}>
                  {cat.nombre}
                </option>
              ))}
            </select>
            <p className="text-xs text-slate-500 mt-1">
              Úsalo si quieres crear subcategorías (Ej: Bebidas {'>'} Gaseosas).
            </p>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Descripción</label>
            <textarea
              value={descripcion}
              onChange={(e) => setDescripcion(e.target.value)}
              className="w-full px-4 py-3 rounded-xl border border-slate-600 bg-slate-700 text-white focus:ring-2 focus:ring-orange-500 outline-none resize-none h-20 placeholder-slate-400"
              placeholder="Breve descripción para el menú..."
            />
          </div>

          <div className="flex items-center gap-2 pt-2">
            <input
              type="checkbox"
              id="activo"
              checked={activo}
              onChange={(e) => setActivo(e.target.checked)}
              className="w-4 h-4 text-orange-600 focus:ring-orange-500 rounded accent-orange-500"
            />
            <label htmlFor="activo" className="text-sm font-medium text-slate-300 cursor-pointer">
              Visible en el menú público
            </label>
          </div>

          {/* Botones */}
          <div className="pt-6 flex gap-3">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2.5 border border-slate-600 text-slate-400 rounded-xl font-bold hover:bg-slate-700 transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              className="flex-1 px-4 py-2.5 bg-orange-600 text-white rounded-xl font-bold hover:bg-orange-500 transition-colors"
            >
              Guardar
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}