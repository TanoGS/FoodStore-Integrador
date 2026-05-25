import React, { useState, useEffect } from 'react';
import { X, AlertTriangle } from 'lucide-react';

interface IngredienteModalProps {
  ingrediente?: any | null;
  onClose: () => void;
  onSave: (payload: any) => void;
}

export default function IngredienteModal({ ingrediente, onClose, onSave }: IngredienteModalProps) {
  // Campos del nuevo esquema corporativo
  const [nombre, setNombre] = useState('');
  const [stock, setStock] = useState<number | ''>('');
  const [stockSeguridad, setStockSeguridad] = useState<number | ''>('');
  const [unidadMedida, setUnidadMedida] = useState('UNIDAD');
  const [costoUnitario, setCostoUnitario] = useState<number | ''>('');
  const [esAlergeno, setEsAlergeno] = useState(false);

  useEffect(() => {
    if (ingrediente) {
      setNombre(ingrediente.nombre || '');
      setStock(ingrediente.stock ?? '');
      setStockSeguridad(ingrediente.stock_seguridad ?? '');
      setUnidadMedida(ingrediente.unidad_medida || 'UNIDAD');
      setCostoUnitario(ingrediente.costo_unitario ?? '');
      setEsAlergeno(ingrediente.es_alergeno || false);
    }
  }, [ingrediente]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave({
      nombre,
      stock: Number(stock),
      stock_seguridad: Number(stockSeguridad),
      unidad_medida: unidadMedida,
      costo_unitario: Number(costoUnitario),
      es_alergeno: esAlergeno,
    });
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg overflow-hidden">
        
        <div className="px-6 py-4 border-b border-gray-100 flex justify-between items-center bg-gray-50">
          <h3 className="font-bold text-lg text-gray-800">
            {ingrediente ? 'Editar Insumo' : 'Alta de Nuevo Insumo'}
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-red-500 transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          
          {/* Fila 1: Nombre */}
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className="block text-sm font-semibold text-gray-700 mb-1">Nombre *</label>
              <input
                type="text"
                required
                value={nombre}
                onChange={(e) => setNombre(e.target.value)}
                className="w-full px-4 py-2 rounded-xl border border-gray-300 focus:ring-2 focus:ring-orange-500 outline-none"
                placeholder="Ej: Carne Picada"
              />
            </div>
          </div>

          {/* Fila 2: Inventario */}
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-1">Stock Actual</label>
              <input
                type="number"
                step="0.01"
                required
                value={stock}
                onChange={(e) => setStock(e.target.value === '' ? '' : Number(e.target.value))}
                className="w-full px-4 py-2 rounded-xl border border-gray-300 focus:ring-2 focus:ring-orange-500 outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-1">Stock Seguridad</label>
              <input
                type="number"
                step="0.01"
                required
                value={stockSeguridad}
                onChange={(e) => setStockSeguridad(e.target.value === '' ? '' : Number(e.target.value))}
                className="w-full px-4 py-2 rounded-xl border border-gray-300 focus:ring-2 focus:ring-orange-500 outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-1">Unidad</label>
              <select
                value={unidadMedida}
                onChange={(e) => setUnidadMedida(e.target.value)}
                className="w-full px-4 py-2 rounded-xl border border-gray-300 focus:ring-2 focus:ring-orange-500 outline-none bg-white"
              >
                <option value="UNIDAD">Unidades</option>
                <option value="KILOGRAMO">Kilogramos</option>
                <option value="LITRO">Litros</option>
              </select>
            </div>
          </div>

          {/* Fila 3: Finanzas y Alertas */}
          <div className="grid grid-cols-2 gap-4 items-end">
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-1">Costo Unitario ($) *</label>
              <input
                type="number"
                step="0.01"
                required
                value={costoUnitario}
                onChange={(e) => setCostoUnitario(e.target.value === '' ? '' : Number(e.target.value))}
                className="w-full px-4 py-2 rounded-xl border border-gray-300 focus:ring-2 focus:ring-orange-500 outline-none"
                placeholder="Ej: 8500.50"
              />
            </div>
            <div className="pb-2">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="alergeno"
                  checked={esAlergeno}
                  onChange={(e) => setEsAlergeno(e.target.checked)}
                  className="w-5 h-5 text-orange-600 focus:ring-orange-500 rounded border-gray-300"
                />
                <label htmlFor="alergeno" className="text-sm font-bold text-red-600 cursor-pointer flex items-center gap-1">
                  <AlertTriangle className="w-4 h-4" /> Marcar como Alérgeno
                </label>
              </div>
            </div>
          </div>

          {/* Botones */}
          <div className="pt-4 flex gap-3">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-xl font-medium hover:bg-gray-50 transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              className="flex-1 px-4 py-2 bg-orange-600 text-white rounded-xl font-bold hover:bg-orange-700 transition-colors"
            >
              Guardar Insumo
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}