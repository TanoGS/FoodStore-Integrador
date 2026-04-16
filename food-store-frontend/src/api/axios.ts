import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export const axiosClient = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Nota: Luego agregaremos los interceptores JWT (EPIC 01).
// Por ahora, las peticiones viajarán sin token para armar el Admin libremente.