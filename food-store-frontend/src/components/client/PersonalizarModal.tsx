import { useState } from 'react';
import { X, Plus, AlertTriangle } from 'lucide-react';
import type { Producto } from '../../types/producto.type';
import { useCartStore } from '../../store/cartStore';

interface PersonalizarModalProps {
  producto: Producto;
  onClose: () => void;
}

export default function PersonalizarModal({ producto, onClose }: PersonalizarModalProps) {
  const addItem = useCartStore(state => state.addItem);
  const [removedIds, setRemovedIds] = useState<Set<number>>(new Set());

  const receta = producto.receta_detallada ?? [];
  const alergenos = receta.filter(r => r.ingrediente.es_alergeno);
  const removibles = receta.filter(r => r.es_removible === true);

  // Si no hay alérgenos ni removibles, agregar directo
  const needsModal = alergenos.length > 0 || removibles.length > 0;

  const toggleIngredient = (id: number) => {
    setRemovedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const handleAgregar = () => {
    // Armar lista de ingredientes removidos con nombre para mostrar en el carrito
    const removedItems = removedIds.size > 0
      ? Array.from(removedIds).map(id => {
          const r = receta.find(x => x.ingrediente_id === id);
          return { id, nombre: r?.ingrediente.nombre ?? `#${id}` };
        })
      : undefined;
    addItem({
      id: producto.id,
      nombre: producto.nombre,
      precio_base: producto.precio,
      imagen_url: producto.imagenes_url?.[0] ?? producto.imagen_url ?? null,
      personalizacion: removedItems,
      subtotal: producto.precio,
    });
    onClose();
  };

  // Modal simple si no hay nada personalizable
  if (!needsModal) {
    return (
      <>
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-[60]" onClick={onClose} />
        <div className="fixed inset-0 flex items-center justify-center z-[70] px-4 pointer-events-none">
          <div className="bg-white rounded-3xl shadow-2xl w-full max-w-sm p-6 pointer-events-auto">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-black text-slate-800">{producto.nombre}</h2>
              <button onClick={onClose} className="text-slate-400 hover:text-slate-700">
                <X className="w-5 h-5" />
              </button>
            </div>
            <p className="text-slate-500 text-sm mb-6">Producto simple sin opciones de personalización.</p>
            <button
              onClick={handleAgregar}
              className="w-full bg-orange-600 hover:bg-orange-700 text-white py-3 rounded-xl font-bold transition-colors"
            >
              Agregar al carrito — ${producto.precio}
            </button>
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-[60]" onClick={onClose} />

      {/* Modal */}
      <div className="fixed inset-0 flex items-center justify-center z-[70] px-4 pointer-events-none">
        <div className="bg-white rounded-3xl shadow-2xl w-full max-w-md pointer-events-auto overflow-hidden">
          {/* Header */}
          <div className="bg-slate-900 text-white px-6 py-5 flex items-center justify-between">
            <div>
              <h2 className="text-xl font-black">Personalizar</h2>
              <p className="text-slate-400 text-sm font-medium">{producto.nombre}</p>
            </div>
            <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors">
              <X className="w-6 h-6" />
            </button>
          </div>

          {/* Body */}
          <div className="px-6 py-5 max-h-[60vh] overflow-y-auto space-y-6">

            {/* Alérgenos */}
            {alergenos.length > 0 && (
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <AlertTriangle className="w-4 h-4 text-amber-500" />
                  <span className="text-sm font-bold text-amber-700 uppercase tracking-wide">
                    Contiene alérgenos
                  </span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {alergenos.map(r => (
                    <span
                      key={r.ingrediente_id}
                      className="bg-amber-100 text-amber-800 text-xs font-bold px-3 py-1.5 rounded-full"
                    >
                      {r.ingrediente.nombre}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Ingredientes removibles */}
            {removibles.length > 0 && (
              <div>
                <p className="text-sm font-bold text-slate-700 mb-3">
                  ¿Querés quitar algo?
                </p>
                <div className="space-y-2">
                  {removibles.map(r => {
                    const isRemoved = removedIds.has(r.ingrediente_id);
                    return (
                      <label
                        key={r.ingrediente_id}
                        className={`flex items-center gap-3 p-3 rounded-xl border-2 cursor-pointer transition-all ${
                          isRemoved
                            ? 'border-red-300 bg-red-50'
                            : 'border-slate-100 hover:border-slate-200 bg-white'
                        }`}
                      >
                        <div
                          className={`w-5 h-5 rounded-md border-2 flex items-center justify-center transition-all ${
                            isRemoved
                              ? 'border-red-500 bg-red-500'
                              : 'border-slate-300 bg-white'
                          }`}
                        >
                          {isRemoved && (
                            <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 12 12" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M2 6l3 3 5-5" />
                            </svg>
                          )}
                        </div>
                        <input
                          type="checkbox"
                          className="sr-only"
                          checked={isRemoved}
                          onChange={() => toggleIngredient(r.ingrediente_id)}
                        />
                        <span className={`text-sm font-medium transition-colors ${
                          isRemoved ? 'text-red-600 line-through' : 'text-slate-700'
                        }`}>
                          {r.ingrediente.nombre}
                        </span>
                        {isRemoved && (
                          <span className="ml-auto text-xs text-red-500 font-bold">Quitado</span>
                        )}
                      </label>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="px-6 py-5 border-t border-slate-100 bg-slate-50">
            {removedIds.size > 0 && (
              <p className="text-xs text-slate-500 mb-3 text-center">
                Se quitaron {removedIds.size} ingrediente{removedIds.size > 1 ? 's' : ''}
              </p>
            )}
            <button
              onClick={handleAgregar}
              className="w-full bg-orange-600 hover:bg-orange-700 active:scale-95 text-white py-3.5 rounded-xl font-bold text-base transition-all shadow-lg shadow-orange-600/20 flex items-center justify-center gap-2"
            >
              <Plus className="w-5 h-5" />
              Agregar al carrito — ${producto.precio}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
