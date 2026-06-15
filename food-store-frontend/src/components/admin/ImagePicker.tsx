import { useState, useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Search, ChevronLeft, ChevronRight, X, Check, ImageIcon, RefreshCw } from 'lucide-react';
import { UploadsService } from '../../services/uploads.service';

interface ImagePickerProps {
  value: string | null;
  onChange: (url: string | null) => void;
  label?: string;
  folder?: string;
}

const IMAGES_PER_PAGE = 12;

export function ImagePicker({
  value,
  onChange,
  label = 'Imagen del producto',
  folder = 'productos',
}: ImagePickerProps) {
  const [query, setQuery] = useState('');
  const [page, setPage] = useState(0);
  const [syncMsg, setSyncMsg] = useState<string | null>(null);
  const [previewError, setPreviewError] = useState(false);
  const queryClient = useQueryClient();

  // Reset error cuando cambia el valor
  useEffect(() => {
    setPreviewError(false);
  }, [value]);

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['imagenes', folder, query, page],
    queryFn: () =>
      UploadsService.listarImagenes(
        page * IMAGES_PER_PAGE,
        IMAGES_PER_PAGE,
        query || undefined,
        folder,
      ),
  });

  const totalPages = data ? Math.max(1, Math.ceil(data.total / IMAGES_PER_PAGE)) : 1;

  const handleSelect = (url: string) => {
    onChange(url === value ? null : url);
  };

  const handleSync = async () => {
    setSyncMsg(null);
    try {
      const result = await UploadsService.sincronizarImagenes(folder);
      // Refrescar la lista
      queryClient.invalidateQueries({ queryKey: ['imagenes', folder] });
      setPage(0);
      const msgs: string[] = [];
      if (result.creados > 0) msgs.push(`${result.creados} nueva(s)`);
      if (result.eliminados > 0) msgs.push(`${result.eliminados} eliminada(s) de Cloudinary`);
      setSyncMsg(msgs.length > 0 ? msgs.join(', ') : 'Ya está sincronizado');
    } catch {
      setSyncMsg('Error al sincronizar');
    }
  };

  return (
    <div className="space-y-3">
      {label && (
        <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider">
          {label}
        </label>
      )}

      {/* Preview de imagen seleccionada */}
      {value && !previewError ? (
        <div className="relative inline-block w-full">
          <div className="relative rounded-xl overflow-hidden border-2 border-green-500 bg-slate-700">
            <img
              src={value}
              alt="Imagen seleccionada"
              className="w-full h-48 object-cover"
              referrerPolicy="no-referrer"
              onError={() => setPreviewError(true)}
            />
            <div className="absolute top-2 left-2 bg-green-600 text-white text-xs font-bold px-2 py-1 rounded-full flex items-center gap-1">
              <Check className="w-3 h-3" /> Seleccionada
            </div>
          </div>
          <button
            type="button"
            onClick={() => { onChange(null); setPreviewError(false); }}
            className="absolute top-2 right-2 p-1.5 bg-red-600 hover:bg-red-500 text-white rounded-full shadow transition-colors"
            title="Quitar imagen"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      ) : (
        <div className="w-full h-48 rounded-xl border-2 border-dashed border-red-600 bg-red-900/20 flex items-center justify-center">
          <div className="text-center text-red-400">
            <ImageIcon className="w-10 h-10 mx-auto mb-2 opacity-50" />
            <p className="text-sm">La imagen no está disponible</p>
            {value && (
              <button
                type="button"
                onClick={() => { onChange(null); setPreviewError(false); }}
                className="mt-2 text-xs underline hover:text-red-300"
              >
                Quitar y seleccionar otra
              </button>
            )}
          </div>
        </div>
      )}

      {/* Buscador */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
        <input
          type="text"
          placeholder="Buscar por nombre..."
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setPage(0);
          }}
          className="w-full pl-9 pr-4 py-2 bg-slate-700 border border-slate-600 rounded-xl text-sm text-white placeholder-slate-400 focus:ring-2 focus:ring-orange-500 outline-none"
        />
      </div>

      {/* Grid de imágenes */}
      {isLoading ? (
        <div className="grid grid-cols-4 gap-2">
          {Array.from({ length: IMAGES_PER_PAGE }).map((_, i) => (
            <div
              key={i}
              className="aspect-square bg-slate-700 rounded-lg animate-pulse"
            />
          ))}
        </div>
      ) : data && data.data.length > 0 ? (
        <div className="grid grid-cols-4 gap-2">
          {data.data.map((img) => {
            const isSelected = img.url === value || img.secure_url === value;
            return (
              <button
                key={img.id}
                type="button"
                onClick={() => handleSelect(img.secure_url || img.url)}
                className={`
                  relative aspect-square rounded-lg overflow-hidden border-2 transition-all
                  ${
                    isSelected
                      ? 'border-orange-500 ring-2 ring-orange-500 ring-offset-2 ring-offset-slate-800'
                      : 'border-slate-600 hover:border-slate-500 hover:scale-105'
                  }
                `}
                title={img.nombre_archivo || img.public_id}
              >
                <img
                  src={img.secure_url || img.url}
                  alt={img.nombre_archivo || `Imagen ${img.id}`}
                  className="w-full h-full object-cover"
                  referrerPolicy="no-referrer"
                />
                {isSelected && (
                  <div className="absolute inset-0 bg-orange-500/30 flex items-center justify-center">
                    <div className="bg-orange-500 rounded-full p-1">
                      <Check className="w-4 h-4 text-white" />
                    </div>
                  </div>
                )}
              </button>
            );
          })}
        </div>
      ) : (
        <div className="border border-slate-700 rounded-xl p-8 text-center text-slate-500">
          <ImageIcon className="w-10 h-10 mx-auto mb-2 opacity-50" />
          <p className="text-sm">
            {query
              ? `No hay imágenes que coincidan con "${query}"`
              : 'No hay imágenes en la galería. Subí algunas desde Cloudinary.'}
          </p>
        </div>
      )}

      {/* Paginación y sync */}
      <div className="flex items-center justify-between pt-2">
        <span className="text-xs text-slate-400">
          {data && data.total > 0
            ? `${data.total} imagen${data.total !== 1 ? 'es' : ''} · Pág. ${page + 1} / ${totalPages}`
            : '0 imágenes'}
        </span>
        <div className="flex items-center gap-2">
          {data && data.total > IMAGES_PER_PAGE && (
            <div className="flex gap-1">
              <button
                type="button"
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                className="p-1.5 rounded-lg border border-slate-600 text-slate-400 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                type="button"
                onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
                className="p-1.5 rounded-lg border border-slate-600 text-slate-400 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          )}
          <button
            type="button"
            onClick={handleSync}
            disabled={isFetching}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-blue-600 text-blue-400 hover:bg-blue-900/30 disabled:opacity-40 disabled:cursor-not-allowed transition-colors text-xs font-bold"
            title="Sincronizar con Cloudinary"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? 'animate-spin' : ''}`} />
            Sync
          </button>
        </div>
      </div>

      {/* Mensaje de sync */}
      {syncMsg && (
        <div className="text-xs text-center text-blue-400 font-bold py-1">
          🔄 {syncMsg}
        </div>
      )}
    </div>
  );
}
