// src/services/auth.service.ts
import api from '../config/axios';

export const AuthService = {
  // Cambiamos Promise<User> por Promise<any> para que acepte el token + los datos del usuario juntos
  async login(email: string, password: string): Promise<any> {
    
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);

    // Como usamos 'api', la baseURL se pone sola. Solo necesitamos '/usuarios/login'
    const { data } = await api.post('/usuarios/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    });

    // Devolvemos absolutamente todo lo que manda FastAPI (Token + Info del usuario)
    return data;
  }
};