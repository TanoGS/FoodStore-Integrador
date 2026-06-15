import axios from '../config/axios';

export interface UploadResponse {
  id: number;
  public_id: string;
  url: string;
  secure_url: string | null;
  formato: string;
  ancho: number;
  alto: number;
  bytes: number;
  folder: string;
  recurso_tipo: string;
  nombre_archivo: string | null;
  creado_en: string;
}

export interface ImagenList {
  data: UploadResponse[];
  total: number;
}

export const UploadsService = {
  /**
   * Sube una imagen a Cloudinary y la persiste en la base de datos.
   * @param file - Archivo de imagen (File/Blob)
   * @param folder - Carpeta destino en Cloudinary (default: "productos")
   * @param nombreArchivo - Nombre amigable para la imagen (opcional)
   */
  subirImagen: async (
    file: File | Blob,
    folder: string = 'productos',
    nombreArchivo?: string,
  ): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('folder', folder);
    if (nombreArchivo) {
      formData.append('nombre_archivo', nombreArchivo);
    }
    const res = await axios.post<UploadResponse>('/imagenes/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return res.data;
  },

  /**
   * Lista imágenes del catálogo con paginación y búsqueda.
   * @param offset - Offset de paginación (default: 0)
   * @param limit - Límite de resultados (default: 12)
   * @param q - Búsqueda por nombre de archivo (opcional)
   * @param folder - Filtrar por carpeta (opcional, ej: "productos")
   */
  listarImagenes: async (
    offset: number = 0,
    limit: number = 12,
    q?: string,
    folder?: string,
  ): Promise<ImagenList> => {
    const res = await axios.get<ImagenList>('/imagenes', {
      params: { offset, limit, q, folder },
    });
    return res.data;
  },

  /**
   * Obtiene una imagen por su ID.
   * @param imagenId - ID de la imagen
   */
  obtenerImagen: async (imagenId: number): Promise<UploadResponse> => {
    const res = await axios.get<UploadResponse>(`/imagenes/${imagenId}`);
    return res.data;
  },

  /**
   * Elimina una imagen (soft-delete en BD + eliminación en Cloudinary).
   * @param imagenId - ID de la imagen
   */
  eliminarImagen: async (imagenId: number): Promise<void> => {
    await axios.delete(`/imagenes/${imagenId}`);
  },

  /**
   * Sincroniza la tabla local de imágenes con Cloudinary.
   * Crea filas para imágenes nuevas y marca huérfanas como eliminadas.
   * @param folder - Carpeta a sincronizar (default: "productos")
   */
  sincronizarImagenes: async (folder: string = 'productos'): Promise<{
    total_en_cloud: number;
    total_en_db: number;
    creados: number;
    eliminados: number;
    carpeta: string;
  }> => {
    const res = await axios.post(`/imagenes/sincronizar?folder=${encodeURIComponent(folder)}`);
    return res.data;
  },
};
