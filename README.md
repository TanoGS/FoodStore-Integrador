
## Food Store - Integrador - Programación IV — UTN

Food Store es una aplicación web full-stack para la gestión integral de un negocio de comidas.

Integrantes: Renzo Sosa, Sponton Giani

Link video Primer Parcial: https://youtu.be/qEJGTZU9tY8

Link videos Segundo Parcial: https://youtu.be/s0FPryARwXo - https://youtu.be/UQ1JCPWzejY

Link video entrega Final: https://www.youtube.com/watch?v=9lfo6rXOykc

---

## RESUMEN TÉCNICO

# Tecnologías Principales

- **Backend:** FastAPI + SQLModel + PostgreSQL
- **Frontend:** React + TypeScript + Tailwind CSS + Vite
- **Tiempo Real:** WebSockets con JWT
- **Pagos:** MercadoPago Checkout PRO
- **Medios:** Cloudinary
- **Testing:** pytest + TestClient

---

# Características Clave

**RBAC completo** (6 roles, 11 permisos)  
**FSM para pedidos** (6 estados validados)  
**Unit of Work** (transacciones atómicas)  
**WebSockets con Rooms** (sala staff + sala privada por usuario)  
**MercadoPago** (checkout PRO + webhook HMAC + sync manual)  
**Cloudinary** (upload firmado + sincronización BD)  
**Escandallo automático** (costo_produccion desde ingredientes)  
**Stock de seguridad** (alertas WebSocket por ingrediente)  
**Costo de envío configurable** (en runtime desde panel admin)  
**Reactivación de soft-deleted** (usuarios, productos, categorías, ingredientes, direcciones)  
**Cookies HttpOnly** (refresh token seguro contra XSS)  
**20+ tests** (pytest con cobertura)  
**API REST** (50+ endpoints documentados en Swagger)  
**Soft delete** (auditoría completa)  

---

# Patrones de Arquitectura

| Patrón | Implementación | Beneficio |
|--------|----------------|-----------|
| **Feature-First** | Módulos organizados por dominio (usuarios, pedido, etc.) | Escalabilidad, mantenibilidad |
| **Repository Pattern** | UnitOfWork por módulo | Desacoplamiento, testabilidad |
| **Unit of Work** | Transacciones atómicas en pedidos | Consistencia de datos |
| **FSM (Finite State Machine)** | Estados de pedido con reglas validadas | Flujo de negocio claro |
| **Dependency Injection** | FastAPI dependencies | Flexibilidad, testing |
| **JWT-based Auth** | Access token (30min) + Refresh token en cookie HttpOnly (7 días) | Seguridad stateless |
| **RBAC (Role-Based Access Control)** | 6 roles con 11 permisos | Control granular de acceso |
| **WebSocket Manager** | Rooms (salas): `staff:pedidos` + `user:{id}` en `app/modules/pedido/ws_manager.py` | Comunicación bidireccional |
| **Cloudinary Integration** | Backend-signed uploads + sincronización BD | Seguridad en manejo de medios |


---


════════════════════════════════════════════════════
  FoodStore — Guía de Instalación y Ejecución
════════════════════════════════════════════════════

1. PRERREQUISITOS
   • Python 3.11+ (recomendado: python.org o Miniconda)
   • Node.js 18+
   • PostgreSQL 14+ (con pgAdmin)
   • Git

    EVITAR Pythons en rutas no estándar (ej: D:\bin\python.exe)
     porque pueden crear venvs con estructura Unix rota.

2. BACKEND (foood-store-backend)
   2.1  Abrir PowerShell en la carpeta del backend
   2.2  Crear y activar entorno virtual:
          python -m venv venv
          .\venv\Scripts\Activate.ps1
   2.3  Instalar dependencias:
          pip install --upgrade pip
          pip install -r requirements.txt
   2.4  Configurar variables de entorno:
          Copy-Item .env.example .env
          # Editar .env con tus credenciales (ver sección 4)
   2.5  Crear la base de datos en PostgreSQL
   2.6  Inicializar la BD (estructura + usuarios de prueba):
          python init_db.py
        → Borra el schema public, crea todas las tablas vacías,
          siembra los 6 usuarios de prueba y sincroniza Alembic.
          (Equivale a: drop schema + create_all + seed usuarios + alembic stamp head)
   2.7  (Opcional) Para aplicar migraciones futuras de Alembic:
          alembic upgrade heads
   2.8  Levantar el servidor:
          uvicorn main:app --reload
        → Swagger UI:  http://127.0.0.1:8000/docs
        → ReDoc:      http://127.0.0.1:8000/redoc

3. FRONTEND (food-store-frontend)
   3.1  Abrir otra terminal en la carpeta del frontend
   3.2  Instalar dependencias:
          npm install
   3.3  Configurar variables de entorno:
          Copy-Item .env.example .env.development
   3.4  Levantar el dev server:
          npm run dev
        → App: http://localhost:5173

4. SERVICIOS EXTERNOS
   4.1  Cloudinary (gestión de imágenes)
        • Crear cuenta gratis: https://cloudinary.com/
        • Dashboard → "Cloud name", "API Key", "API Secret"
        • Pegar en .env: CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY,
          CLOUDINARY_API_SECRET

   4.2  MercadoPago (pagos)
        • Crear app TEST: https://www.mercadopago.com.ar/developers/panel
        • Copiar Access Token y Public Key
        • Pegar en .env: MP_ACCESS_TOKEN, MP_PUBLIC_KEY

   4.3  ngrok (webhooks en desarrollo)
        • Descargar: https://ngrok.com/download
        • Crear cuenta y obtener authtoken
        • ngrok config add-authtoken <TU_TOKEN>
        • ngrok http 8000
        • Copiar la URL https://...ngrok-free.app
        • Actualizar MP_NOTIFICATION_URL y CORS_ORIGINS en .env

5. CREDENCIALES POR DEFECTO
   Admin:            admin@foodstore.com        /  admin123
   Cajero:           cajero@foodstore.com       /  cajero123
   Cliente:          pepe@gmail.com             /  pepe123
   Gestor Stock:     stock@foodstore.com        /  stock123
   Gestor Pedidos:   pedidos@foodstore.com      /  pedidos123
   Cocina:           cocina@foodstore.com       /  cocina123

6. TROUBLESHOOTING
   • "error 103 al crear venv" → Usá el Python de Miniconda
   • "Invalid cloud_name" → Revisá CLOUDINARY_CLOUD_NAME
   • "CORS policy" → Verificar que la URL del front esté en CORS_ORIGINS
   • Puerto 8000 ocupado → netstat -ano | findstr :8000

════════════════════════════════════════════════════
