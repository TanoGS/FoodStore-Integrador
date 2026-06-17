// src/types/auth.type.ts
// Tipos de autenticación y usuario, alineados con los schemas del backend.

export interface Rol {
  codigo:      string; // 'ADMIN' | 'CLIENTE' | 'GESTOR_STOCK' | 'GESTOR_PEDIDOS' | 'CAJERO' | 'COCINA'
  nombre:      string;
  descripcion?: string;
}

export interface Usuario {
  id:         number;
  email:      string;
  nombre:     string;
  apellido:   string;
  cel?:       string | null;
  activo:     boolean;
  roles:      Rol[];
  creado_en?: string;
}

export interface LoginRequest {
  email:    string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type:   string;
  usuario:      Usuario;
}

export interface RegisterRequest {
  nombre:   string;
  apellido: string;
  email:    string;
  password: string;
  cel?:     string;
}
