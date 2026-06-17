// src/services/auth.service.ts
import api from '../config/axios';
import type { Usuario } from '../types/auth.type';

export interface LoginResponse {
  access_token: string;
  token_type:   string;
  usuario:      Usuario;
}

export const AuthService = {
  async login(email: string, password: string): Promise<LoginResponse> {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);

    const { data } = await api.post<LoginResponse>('/usuarios/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    // El backend setea la cookie HttpOnly access_token automáticamente.
    // Solo devolvemos los datos del usuario al caller.
    return data;
  },

  async logout(): Promise<void> {
    await api.post('/usuarios/logout');
  },
};