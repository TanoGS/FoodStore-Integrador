import api from '../config/axios';

// El prefijo base se completa solo desde la instancia `api` (VITE_API_URL).
// El token (Bearer) y la cookie HttpOnly los inyectan los interceptores de `api`.

export const UsuarioService = {
  listar: async () => {
    // GET /api/usuarios/gestion -> List[UsuarioPublic] (array directo)
    const response = await api.get('/usuarios/gestion');
    return response.data;
  },

  crear: async (datos: any) => {
    const response = await api.post('/usuarios/registro', datos);
    return response.data;
  },

  actualizar: async (id: number, datos: any) => {
    const response = await api.patch(`/usuarios/${id}`, datos);
    return response.data;
  },

  /** Reemplaza completamente los roles de un usuario. Solo ADMIN. */
  asignarRoles: async (id: number, role_codigos: string[]) => {
    const response = await api.patch(`/usuarios/${id}/roles`, { role_codigos });
    return response.data;
  },

  eliminar: async (id: number) => {
    const response = await api.delete(`/usuarios/${id}`);
    return response.data;
  },

  reactivar: async (id: number) => {
    const response = await api.patch(`/usuarios/${id}/reactivar`);
    return response.data;
  }
};
