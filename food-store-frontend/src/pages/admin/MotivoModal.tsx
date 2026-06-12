import { useEffect, useState } from 'react';
import { X, AlertTriangle } from 'lucide-react';

interface MotivoModalProps {
  open: boolean;
  onClose: () => void;
  onConfirm: (motivo: string) => void;
}

const MAX_MOTIVO = 200;

/**
 * Modal liviano para pedir el motivo de cancelación de un pedido.
 * El backend (AvanzarEstadoRequest en schemas.py) exige `motivo` no vacío
 * cuando el estado destino es CANCELADO.
 *
 * Mismo patrón visual que los modales existentes del proyecto
 * (PanelUsuarios.tsx, ProductoModal.tsx).
 */
export default function MotivoModal({ open, onClose, onConfirm }: MotivoModalProps) {
  const [motivo, setMotivo] = useState('');
  const [error, setError]   = useState<string | null>(null);

  // Reset al abrir/cerrar
  useEffect(() => {
    if (open) {
      setMotivo('');
      setError(null);
    }
  }, [open]);

  // Cerrar con Escape
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open, onClose]);

  if (!open) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = motivo.trim();
    if (trimmed.length === 0) {
      setError('El motivo es obligatorio para cancelar un pedido.');
      return;
    }
    if (trimmed.length > MAX_MOTIVO) {
      setError(`El motivo no puede superar los ${MAX_MOTIVO} caracteres.`);
      return;
    }
    onConfirm(trimmed);
  };

  const restantes = MAX_MOTIVO - motivo.length;

  return (
    <div
      className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center z-50 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="motivo-modal-title"
    >
      <div className="bg-slate-800 rounded-2xl w-full max-w-md shadow-2xl overflow-hidden border border-slate-700">
        {/* Cabecera */}
        <div className="bg-slate-700 p-5 text-white flex justify-between items-center">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-red-400" />
            <h2 id="motivo-modal-title" className="text-lg font-black">
              Cancelar pedido
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-red-400 transition-colors"
            aria-label="Cerrar"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Cuerpo */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <p className="text-sm text-slate-400">
            Esta acción cancelará el pedido. Por política del sistema,
            el motivo es <span className="font-bold text-white">obligatorio</span>{' '}
            y quedará registrado en el historial.
          </p>

          <div>
            <label
              htmlFor="motivo"
              className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2"
            >
              Motivo de cancelación *
            </label>
            <textarea
              id="motivo"
              value={motivo}
              onChange={(e) => {
                setMotivo(e.target.value);
                if (error) setError(null);
              }}
              rows={4}
              maxLength={MAX_MOTIVO}
              placeholder="Ej: Cliente solicitó cancelación por demora, falta de stock, etc."
              className={`w-full px-4 py-3 border rounded-xl outline-none focus:ring-2 focus:ring-orange-500 resize-none text-sm ${
                error ? 'border-red-500 bg-red-900/20 text-red-300' : 'border-slate-600 bg-slate-700 text-white placeholder-slate-500'
              }`}
              autoFocus
            />
            <div className="flex justify-between items-center mt-2">
              {error ? (
                <span className="text-xs font-bold text-red-400">{error}</span>
              ) : (
                <span className="text-xs text-slate-500">
                  Mínimo 1 carácter.
                </span>
              )}
              <span
                className={`text-xs ${
                  restantes < 20 ? 'text-orange-400 font-bold' : 'text-slate-500'
                }`}
              >
                {restantes} restantes
              </span>
            </div>
          </div>

          {/* Footer */}
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-5 py-2.5 text-slate-400 font-bold hover:bg-slate-700 rounded-xl transition-colors"
            >
              Volver
            </button>
            <button
              type="submit"
              className="px-5 py-2.5 bg-red-600 text-white rounded-xl font-bold hover:bg-red-500 transition-colors shadow-lg shadow-red-600/20"
            >
              Confirmar cancelación
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
