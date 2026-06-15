import { useState, useRef, useCallback } from 'react';
import { UploadsService } from '../../services/uploads.service';
import type { UploadResponse } from '../../services/uploads.service';

interface ImageUploaderProps {
  /** URL de imagen actual (para editar) */
  currentUrl?: string | null;
  /** Callback cuando se sube una imagen nueva */
  onUpload: (url: string, publicId: string) => void;
  /** Callback cuando se elimina la imagen */
  onRemove?: () => void;
  /** Carpeta en Cloudinary (default: productos) */
  folder?: string;
  /** Texto del label */
  label?: string;
}

const MAX_SIZE_MB = 5;
const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/webp'];

export function ImageUploader({
  currentUrl,
  onUpload,
  onRemove,
  folder = 'productos',
  label = 'Imagen del producto',
}: ImageUploaderProps) {
  const [preview, setPreview] = useState<string | null>(currentUrl || null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const validateFile = (file: File): string | null => {
    if (!ACCEPTED_TYPES.includes(file.type)) {
      return `Tipo de archivo no permitido. Usá: JPG, PNG o WEBP.`;
    }
    if (file.size > MAX_SIZE_MB * 1024 * 1024) {
      return `El archivo supera el límite de ${MAX_SIZE_MB} MB.`;
    }
    return null;
  };

  const handleFile = useCallback(async (file: File) => {
    const validationError = validateFile(file);
    if (validationError) {
      setError(validationError);
      return;
    }

    setError(null);
    setUploading(true);

    // Preview local
    const localPreview = URL.createObjectURL(file);
    setPreview(localPreview);

    try {
      const result: UploadResponse = await UploadsService.subirImagen(file, folder);
      // Limpiar preview local y usar el de Cloudinary
      URL.revokeObjectURL(localPreview);
      setPreview(result.url);
      onUpload(result.url, result.public_id);
      setError(null);
    } catch (err: unknown) {
      // Restaurar preview anterior
      URL.revokeObjectURL(localPreview);
      setPreview(currentUrl || null);
      // Extraer mensaje de error del backend
      let message = 'Error al subir la imagen';
      if (
        err &&
        typeof err === 'object' &&
        'response' in err &&
        (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
      ) {
        message = (err as { response: { data: { detail: string } } }).response.data.detail;
      } else if (err instanceof Error) {
        message = err.message;
      }
      setError(message);
    } finally {
      setUploading(false);
    }
  }, [folder, onUpload, currentUrl]);

  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, [handleFile]);

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => setDragOver(false);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  const handleRemove = () => {
    setPreview(null);
    onRemove?.();
  };

  const handleClick = () => {
    inputRef.current?.click();
  };

  return (
    <div className="space-y-2">
      {label && (
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-200">
          {label}
        </label>
      )}

      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_TYPES.join(',')}
        className="hidden"
        onChange={handleInputChange}
        disabled={uploading}
      />

      {preview ? (
        // Preview de imagen
        <div className="relative inline-block">
          <img
            src={preview}
            alt="Preview"
            className="w-full max-w-xs h-48 object-cover rounded-lg border border-gray-300 dark:border-gray-600"
          />
          <div className="absolute top-2 right-2 flex gap-1">
            <button
              type="button"
              onClick={handleClick}
              disabled={uploading}
              className="p-1.5 bg-white dark:bg-gray-800 rounded-full shadow hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              title="Cambiar imagen"
            >
              <svg className="w-4 h-4 text-gray-600 dark:text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
              </svg>
            </button>
            <button
              type="button"
              onClick={handleRemove}
              disabled={uploading}
              className="p-1.5 bg-white dark:bg-gray-800 rounded-full shadow hover:bg-red-50 dark:hover:bg-red-900 transition-colors"
              title="Quitar imagen"
            >
              <svg className="w-4 h-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          {uploading && (
            <div className="absolute inset-0 bg-black/40 rounded-lg flex items-center justify-center">
              <div className="flex flex-col items-center gap-2">
                <div className="w-8 h-8 border-3 border-white border-t-transparent rounded-full animate-spin" />
                <span className="text-white text-sm">Subiendo...</span>
              </div>
            </div>
          )}
        </div>
      ) : (
        // Zona de drop
        <div
          onClick={handleClick}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          className={`
            w-full h-48 border-2 border-dashed rounded-lg cursor-pointer
            flex flex-col items-center justify-center gap-3
            transition-all duration-200
            ${dragOver
              ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
              : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'
            }
            ${uploading ? 'pointer-events-none opacity-50' : ''}
          `}
        >
          <svg className="w-10 h-10 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
              d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
            />
          </svg>
          <div className="text-center">
            <p className="text-sm font-medium text-gray-600 dark:text-gray-300">
              Arrastrá una imagen o hacé clic para seleccionar
            </p>
            <p className="text-xs text-gray-400 mt-1">
              JPG, PNG o WEBP • Máx {MAX_SIZE_MB} MB
            </p>
          </div>
        </div>
      )}

      {error && (
        <p className="text-sm text-red-600 dark:text-red-400 flex items-center gap-1">
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
          {error}
        </p>
      )}
    </div>
  );
}