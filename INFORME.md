## INFORME

# TPI Programación IV — UTN

**Integrantes:** Renzo Sosa, Sponton Giani

---

## TABLA DE CONTENIDOS

1. [Resumen Ejecutivo](#1-resumen-ejecutivo)
2. [Stack Tecnológico](#2-stack-tecnológico)
3. [Arquitectura General](#3-arquitectura-general)
4. [Módulos del Backend](#4-módulos-del-backend)
5. [Frontend - Estructura y Componentes](#5-frontend---estructura-y-componentes)
6. [Modelo de Datos](#6-modelo-de-datos)
7. [API REST - Endpoints](#7-api-rest---endpoints)
8. [Sistema de Seguridad y RBAC](#8-sistema-de-seguridad-y-rbac)
9. [Integraciones Externas](#9-integraciones-externas)
10. [WebSockets - Comunicación Tiempo Real](#10-websockets---comunicación-tiempo-real)
11. [Testing y QA](#11-testing-y-qa)
12. [Gestión de Archivos y Medios](#12-gestión-de-archivos-y-medios)

---

## 1. RESUMEN EJECUTIVO

### Descripción del Proyecto

**FoodStore** es una plataforma integral de comercio electrónico especializada en comidas y bebidas, desarrollada con arquitectura moderna y completamente escalable. Proporciona funcionalidades para:

- **Clientes:** Catálogo de productos, carrito, pedidos, pagos online
- **Administración:** Gestión de inventario, usuarios, estadísticas, control de pedidos
- **Personal Operativo:** Vistas especializadas para cocina, caja y logística

---

## 2. STACK TECNOLÓGICO

### 2.1 Backend

| Componente | Versión | Propósito |
|-----------|---------|----------|
| **FastAPI** | 0.135.3 | Framework web asincrónico |
| **Python** | 3.9+ | Lenguaje de programación |
| **SQLModel** | 0.0.38 | ORM híbrido (SQLAlchemy + Pydantic) |
| **PostgreSQL** | 15+ | Base de datos relacional |
| **Alembic** | 1.18.4 | Migraciones de base de datos |
| **python-jose** | 3.5.0 | Generación y validación de JWT |
| **bcrypt** | 4.0.1 | Hashing de contraseñas |
| **passlib** | 1.7.4 | Gestión de contraseñas |
| **python-multipart** | 0.0.27 | Soporte para formularios multipart |
| **pydantic** | 2.13.0 | Validación de datos |
| **pydantic-settings** | 2.13.1 | Configuración con variables de entorno |
| **python-dotenv** | 1.2.2 | Gestión de variables de entorno |
| **uvicorn** | 0.44.0 | Servidor ASGI |
| **mercadopago** | 2.3.0 | SDK de MercadoPago |
| **cloudinary** | 1.36.0 | Cliente de Cloudinary |
| **websockets** | 13.0 | Soporte WebSocket |
| **psycopg2-binary** | 2.9.11 | Driver PostgreSQL |
| **psycopg2** | 2.9.12 | Driver PostgreSQL |
| **SQLAlchemy** | 2.0.49 | ORM base |
| **pytest** | 8.3.4 | Framework de testing |
| **pytest-asyncio** | 0.24.0 | Testing asincrónico |
| **pytest-cov** | 5.0.0 | Cobertura de tests |
| **pytest-dotenv** | 0.5.2 | Variables de entorno en tests |
| **httpx** | 0.28.1 | Cliente HTTP para tests |

### 2.2 Frontend

| Componente | Versión | Propósito |
|-----------|---------|----------|
| **React** | 19.2.4 | Librería UI y gestión de componentes |
| **TypeScript** | ~6.0.2 | Tipado estático para JavaScript |
| **Vite** | ^8.0.4 | Build tool y dev server |
| **React Router DOM** | ^7.14.1 | Enrutamiento en SPA |
| **Tailwind CSS** | ^4.2.2 | Framework CSS utility-first |
| **@tanstack/react-query** | ^5.99.0 | Gestión de estado asincrónico (servidor) |
| **@tanstack/react-form** | ^1.29.0 | Gestión avanzada de formularios |
| **Zustand** | ^5.0.12 | Gestión de estado global ligera |
| **Axios** | ^1.15.0 | Cliente HTTP |
| **Recharts** | ^3.8.1 | Librería de gráficos |
| **Lucide React** | ^1.11.0 | Iconografía SVG |
| **@mercadopago/sdk-react** | ^1.0.7 | SDK de MercadoPago para React |

### 2.3 Herramientas DevOps y Testing

| Herramienta | Propósito |
|-----------|----------|
| **Alembic** | Control de versiones de esquema BD |
| **pytest** | Testing unitario e integración |
| **ESLint** | Linting de código JavaScript |
| **PostCSS** | Procesamiento de CSS |
| **Git** | Control de versiones |
| **pytest-asyncio** | Testing de funciones asincrónicas |

---

## 3. ARQUITECTURA GENERAL

### 3.1 Diagrama de Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React + Vite)                  │
├─────────────────────────────────────────────────────────────────┤
│  Pages (Home, Menu, Checkout, Dashboard, Admin)                 │
│  Components (Layout, Client, Admin, Common)                     │
│  Stores (Zustand) → Auth, Cart, Pedido, Theme, WebSocket       │
│  Services (Axios) → API calls                                   │
│  Hooks → useRole, usePedidoWebSocket, useAdminOrdersFeed        │
│  ProtectedRoute → RBAC en routing                               │
└─────────────┬──────────────────────────┬────────────────────────┘
              │ HTTP/REST + WebSocket    │
              │ (Token JWT en headers)   │
              │                          │
┌─────────────▼──────────────────────────▼────────────────────────┐
│                    BACKEND GATEWAY (FastAPI)                    │
├─────────────────────────────────────────────────────────────────┤
│  TimingMiddleware | RateLimitMiddleware | CORSMiddleware          │
│  Exception Handlers (AppError + Genérico)                      │
│  Lifespan (startup/shutdown)                                    │
└──────────┬────────────────────────────┬──────────────────────────┘
           │                            │
    ┌──────▼────────────┐       ┌──────▼──────────┐
    │   REST API        │       │  WebSocket      │
    │   (/api/v1)       │       │  /ws/pedidos    │
    │                   │       │                 │
    │ Modules:          │       │ Features:       │
    │ - Usuarios (auth) │       │ - Rooms:staff   │
    │ - Pedidos         │       │ - Rooms:user:{id}│
    │ - Pagos           │       │ - JWT auth      │
    │ - Direcciones     │       │ - Pool conex.   │
    │ - Catalogo        │       └─────────────────┘
    │ - Admin           │
    │ - Imagenes        │
    └──────┬────────────┘
           │
┌──────────▼────────────────────────────────────────────────────┐
│           SERVICE LAYER (Business Logic)                      │
├────────────────────────────────────────────────────────────┤
│ - UsuarioService      - ProductoService (Escandallo)         │
│ - PedidoService (FSM) - CategoriaService                     │
│ - PagoService        - IngredienteService                   │
│ - DireccionService   - ImagenService (Cloudinary)           │
│ - AdminService       - EstadisticasService                  │
└──────────┬─────────────────────────────────────────────────┘
           │
┌──────────▼────────────────────────────────────────────────────┐
│        DATA ACCESS LAYER (Repository + UoW)                   │
├────────────────────────────────────────────────────────────┤
│ - GenericRepository                                        │
│ - UnitOfWork (transacciones atómicas)                      │
│ - Stock validation + seguridad alerts                       │
└──────────┬─────────────────────────────────────────────────┘
           │
  ┌────────▼──────────┬──────────────┬──────────────┐
  │                   │              │              │
  ▼                   ▼              ▼              ▼
PostgreSQL      MercadoPago     Cloudinary    Tiempo Real
(BD principal)  (Pagos)         (Imágenes)    (WebSocket)
```

### 3.2 Patrones de Arquitectura

| Patrón | Implementación | Beneficio |
|--------|----------------|-----------|
| **Feature-First** | Módulos organizados por dominio (usuarios, pedido, etc.) | Escalabilidad, mantenibilidad |
| **Repository Pattern** | UnitOfWork por módulo | Desacoplamiento, testabilidad |
| **Unit of Work** | Transacciones atómicas en pedidos | Consistencia de datos |
| **FSM (Finite State Machine)** | Estados de pedido con reglas validadas | Flujo de negocio claro |
| **Dependency Injection** | FastAPI dependencies | Flexibilidad, testing |
| **JWT-based Auth** | Tokens access (30min) + refresh (7 días) en cookies | Seguridad stateless |
| **RBAC (Role-Based Access Control)** | 6 roles con permisos granulares | Control granular de acceso |
| **WebSocket Manager** | Rooms por usuario + sala staff | Comunicación bidireccional |
| **Cloudinary Integration** | Backend-signed uploads | Seguridad en manejo de medios |
| **Stock Safety Alerts** | Ingredientes con stock de seguridad | Notificaciones automáticas |

---

## 4. MÓDULOS DEL BACKEND

### 4.1 Estructura de Carpetas

```
foood-store-backend/
├── app/
│   ├── modules/
│   │   ├── auth/              # Schemas y dependencias compartidas
│   │   ├── usuario/           # Auth + gestión de usuarios
│   │   │   ├── models.py
│   │   │   ├── repository.py
│   │   │   ├── router.py
│   │   │   ├── schemas.py
│   │   │   ├── service.py
│   │   │   └── unit_of_work.py
│   │   ├── direccion/         # Direcciones de entrega
│   │   │   ├── models.py
│   │   │   ├── repository.py
│   │   │   ├── router.py
│   │   │   ├── schemas.py
│   │   │   ├── service.py
│   │   │   └── unit_of_work.py
│   │   ├── catalogo/          # Productos e ingredientes
│   │   │   ├── router.py
│   │   │   ├── shared_models.py
│   │   │   ├── categoria/
│   │   │   │   ├── models.py, repository.py, router.py, schemas.py, service.py, unit_of_work.py
│   │   │   ├── producto/
│   │   │   │   ├── models.py, repository.py, router.py, schemas.py, service.py, unit_of_work.py
│   │   │   └── ingrediente/
│   │   │       ├── models.py, repository.py, router.py, schemas.py, service.py, unit_of_work.py
│   │   ├── pedido/            # Dominio central (FSM, UoW, WebSocket)
│   │   │   ├── models.py
│   │   │   ├── repository.py
│   │   │   ├── router.py
│   │   │   ├── schemas.py
│   │   │   ├── service.py
│   │   │   ├── unit_of_work.py
│   │   │   ├── stock.py      # Validación de stock + alertas
│   │   │   ├── events.py     # Payloads de eventos WS
│   │   │   ├── ws_manager.py # ConnectionManager
│   │   │   └── ws_router.py  # Endpoint WebSocket
│   │   ├── pagos/             # Integración MercadoPago
│   │   │   ├── models.py
│   │   │   ├── repository.py
│   │   │   ├── router.py
│   │   │   ├── schemas.py
│   │   │   ├── service.py
│   │   │   └── unit_of_work.py
│   │   ├── imagenes/          # Uploads Cloudinary
│   │   │   ├── models.py
│   │   │   ├── repository.py
│   │   │   ├── router.py
│   │   │   ├── schemas.py
│   │   │   ├── service.py
│   │   │   └── unit_of_work.py
│   │   └── admin/             # Dashboard y configuración
│   │       └── router.py      # KPIs, rentabilidad, costo envío
│   └── __init__.py
├── core/
│   ├── config.py          # Variables de entorno (Settings)
│   ├── database.py        # Conexión y sesión
│   ├── db.py              # Alias de database
│   ├── security.py        # JWT, contraseñas, CORS, RoleChecker
│   ├── repository.py      # GenericRepository
│   ├── unit_of_work.py    # Patrón UoW base
│   ├── exceptions.py      # AppError y handlers
│   ├── rate_limit.py      # RateLimitMiddleware
│   └── settings_runtime.py # Configuración en runtime (costo envío)
├── alembic/               # Migraciones de BD
├── tests/                 # Suite de tests
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_pagos_crear.py
│   │   ├── test_pedido_fsm.py
│   │   └── test_pedido_schemas.py
│   └── integration/
│       ├── test_auth.py
│       ├── test_pagos_sincronizar.py
│       ├── test_pagos_webhook.py
│       ├── test_pedido_crud.py
│       └── test_pedido_estado.py
├── main.py                # Punto de entrada (FastAPI app)
├── init_db.py             # Script de inicialización
├── requirements.txt       # Dependencias Python
└── pytest.ini             # Configuración de pytest
```

### 4.2 Módulos Implementados (8 routers principales)

#### **4.2.1 Usuarios (Autenticación + Gestión de usuarios)**

**Propósito:** Registro, login, logout, refresh tokens, CRUD de usuarios y asignación de roles

**Endpoints:**
- `POST /api/v1/usuarios/registro` - Registro de nuevo usuario
- `POST /api/v1/usuarios/login` - Autenticación (OAuth2PasswordRequestForm)
- `POST /api/v1/usuarios/logout` - Cierre de sesión y revocación
- `POST /api/v1/usuarios/refresh` - Renovación de access token (cookie HttpOnly)
- `GET /api/v1/usuarios/me` - Perfil del usuario autenticado
- `PATCH /api/v1/usuarios/me` - Actualizar perfil propio
- `POST /api/v1/usuarios/me/cambiar-password` - Cambiar contraseña con verificación
- `GET /api/v1/usuarios` - Listar usuarios activos (ADMIN, con paginación y filtro por rol)
- `GET /api/v1/usuarios/gestion` - Listar TODOS los usuarios activos e inactivos (ADMIN)
- `GET /api/v1/usuarios/{id}` - Detalle de usuario (ADMIN)
- `PATCH /api/v1/usuarios/{id}` - Editar usuario (ADMIN)
- `PATCH /api/v1/usuarios/{id}/roles` - Asignar roles (ADMIN)
- `DELETE /api/v1/usuarios/{id}` - Soft delete (ADMIN)
- `PATCH /api/v1/usuarios/{id}/reactivar` - Reactivar usuario eliminado (ADMIN)

**Tecnología:**
- Contraseñas hasheadas con bcrypt
- JWT access token: 30 minutos
- JWT refresh token: 7 días (en cookie HttpOnly)
- Rate limiting: 5 intentos fallidos en 15 minutos
- Refresh token rotation

#### **4.2.2 Pedidos (Dominio Central)**

**Propósito:** Gestión completa del ciclo de vida de pedidos con FSM

**Endpoints:**
- `POST /api/v1/pedidos` - Crear pedido (UoW atómico)
- `GET /api/v1/pedidos` - Listar pedidos con paginación (propios para cliente, todos para staff)
- `GET /api/v1/pedidos/{id}` - Detalle con historial
- `GET /api/v1/pedidos/{id}/historial` - Historial de estados del pedido
- `PATCH /api/v1/pedidos/{id}/estado` - Avanzar FSM (staff: ADMIN/GESTOR_PEDIDOS/CAJERO/COCINA)
- `PATCH /api/v1/pedidos/{id}/cancelar` - Cancelar pedido con motivo (cliente o staff)
- `GET /api/v1/pedidos/admin` - Lista enriquecida para staff (con cliente, dirección, productos)
- `GET /api/v1/pedidos/gestion/todos` - Lista completa para administración

**Características:**
- **FSM 6 estados:** PENDIENTE → CONFIRMADO → EN_PREPARACION → EN_CAMINO → ENTREGADO / CANCELADO
- **Validaciones de transición:** Solo transiciones válidas permitidas
- **Historial append-only:** Registro inmutable de cambios de estado con motivo
- **Unit of Work:** Transacciones atómicas
- **Snapshots de datos:** Captura de precios y nombres históricos
- **Validaciones de stock:** Pre-validación al crear pedido
- **Stock de seguridad:** Alertas WebSocket cuando ingredientes cruzan umbral
- **WebSocket privado:** `pedido.mio.actualizado` a sala del cliente

**Máquina de Estados:**

| Estado | Orden | Terminal | Puede pasar a |
|--------|-------|----------|---------------|
| PENDIENTE | 1 | No | CONFIRMADO, CANCELADO |
| CONFIRMADO | 2 | No | EN_PREPARACION, CANCELADO |
| EN_PREPARACION | 3 | No | EN_CAMINO, CANCELADO |
| EN_CAMINO | 4 | No | ENTREGADO |
| ENTREGADO | 5 | ✅ Sí | — (terminal) |
| CANCELADO | 6 | ✅ Sí | — (terminal) |

#### **4.2.3 Direcciones (Gestión de direcciones)**

**Propósito:** CRUD completo de direcciones de entrega por usuario

**Endpoints:**
- `GET /api/v1/direcciones` - Listar direcciones del usuario
- `POST /api/v1/direcciones` - Crear nueva dirección
- `GET /api/v1/direcciones/{id}` - Obtener una dirección específica
- `PATCH /api/v1/direcciones/{id}` - Editar dirección
- `PATCH /api/v1/direcciones/{id}/principal` - Marcar como principal
- `DELETE /api/v1/direcciones/{id}` - Soft delete (con validación de dirección principal)
- `PATCH /api/v1/direcciones/{id}/reactivar` - Reactivar dirección eliminada

**Características:**
- Una dirección principal por usuario
- Campos de geolocalización (calle, número, piso, depto, ciudad, provincia, CP)
- Referencias personalizadas
- Reactivación de soft-deleted

#### **4.2.4 Catálogo (Productos, Categorías e Ingredientes)**

**Propósito:** Gestión del catálogo de productos con escandallo automático

**Router base:** `/api/v1/catalogo`

**Sub-módulos:**

**Categorías (`/catalogo/categorias`):**
- `GET /catalogo/categorias` - Listar categorías (soporta `solo_raiz`, `parent_id`, `incluir_eliminados`)
- `POST /catalogo/categorias` - Crear categoría (ADMIN/GESTOR_STOCK)
- `GET /catalogo/categorias/{id}` - Detalle con subcategorías
- `PATCH /catalogo/categorias/{id}` - Editar categoría
- `PATCH /catalogo/categorias/{id}/visibilidad` - Toggle activo (ADMIN/GESTOR_STOCK)
- `PATCH /catalogo/categorias/{id}/reactivar` - Reactivar (ADMIN/GESTOR_STOCK)
- `DELETE /catalogo/categorias/{id}` - Soft delete con validación de hijos/productos

**Productos (`/catalogo/productos`):**
- `GET /catalogo/productos` - Listar con filtros (categoría, activo, búsqueda)
- `POST /catalogo/productos` - Crear producto con escandallo automático (ADMIN/GESTOR_STOCK)
- `GET /catalogo/productos/{id}` - Detalle con receta completa
- `PATCH /catalogo/productos/{id}` - Actualizar producto y recalcular escandallo
- `PATCH /catalogo/productos/{id}/disponibilidad` - Toggle activo (ADMIN/GESTOR_STOCK)
- `PATCH /catalogo/productos/{id}/imagenes` - Reemplazar array de imágenes (ADMIN/GESTOR_STOCK)
- `PATCH /catalogo/productos/{id}/reactivar` - Reactivar producto (ADMIN/GESTOR_STOCK)
- `DELETE /catalogo/productos/{id}` - Soft delete (ADMIN/GESTOR_STOCK)

**Ingredientes (`/catalogo/ingredientes`):**
- `GET /catalogo/ingredientes` - Listar ingredientes
- `POST /catalogo/ingredientes` - Crear ingrediente (ADMIN/GESTOR_STOCK)
- `GET /catalogo/ingredientes/{id}` - Detalle
- `PATCH /catalogo/ingredientes/{id}` - Actualizar ingrediente (ADMIN/GESTOR_STOCK)
- `PATCH /catalogo/ingredientes/{id}/reactivar` - Reactivar (ADMIN/GESTOR_STOCK)
- `DELETE /catalogo/ingredientes/{id}` - Soft delete (ADMIN/GESTOR_STOCK)

**Características:**
- **Escandallo automático:** `costo_produccion` se calcula desde la suma de ingredientes × cantidad_requerida × costo_unitario
- Categorías jerárquicas (parent_id)
- Stock dinámico
- Múltiples imágenes por producto (`imagenes_url[]`)
- Flags de alergenicidad en ingredientes
- **Stock de seguridad:** Cada ingrediente tiene un umbral mínimo (`stock_seguridad`)

#### **4.2.5 Pagos (Integración MercadoPago)**

**Propósito:** Gestión de pagos online con MercadoPago Checkout PRO

**Endpoints:**
- `POST /api/v1/pagos/crear` - Crear preference de MercadoPago
- `POST /api/v1/pagos/webhook` - Webhook IPN (público, valida firma HMAC-SHA256)
- `GET /api/v1/pagos/redirect/success` - Redirección post-aprobación
- `GET /api/v1/pagos/redirect/failure` - Redirección post-rechazo
- `GET /api/v1/pagos/redirect/pending` - Redirección post-pendiente
- `GET /api/v1/pagos/{pedido_id}` - Consultar estado del pago
- `POST /api/v1/pagos/{pedido_id}/sincronizar` - Sincronización manual con MP (staff)

**Características:**
- Checkout PRO de MercadoPago
- Tokenización segura de tarjetas
- Webhook IPN con validación de firma HMAC-SHA256
- Idempotency keys UUID
- Estados: pending → approved → rejected
- Redirecciones para flujo completo (MP → backend → frontend)
- Sincronización manual para casos donde el webhook no llegó

**Formas de pago soportadas:**
- **MercadoPago:** Para DELIVERY (obligatorio)
- **Efectivo:** Para EN_LOCAL (pedido queda en PENDIENTE)

#### **4.2.6 Imágenes (Gestión de medios con Cloudinary)**

**Propósito:** Upload, sincronización y eliminación de imágenes

**Endpoints:**
- `POST /api/v1/imagenes/upload` - Upload de imagen (ADMIN/GESTOR_STOCK)
- `GET /api/v1/imagenes` - Listar imágenes con paginación y filtros (ADMIN/GESTOR_STOCK)
- `GET /api/v1/imagenes/{id}` - Obtener imagen por ID (ADMIN/GESTOR_STOCK)
- `POST /api/v1/imagenes/sincronizar` - Sincronizar BD con Cloudinary (ADMIN/GESTOR_STOCK)
- `DELETE /api/v1/imagenes/{id}` - Eliminar registro de BD (ADMIN/GESTOR_STOCK)
- `DELETE /api/v1/imagenes/cloudinary/{public_id}` - Eliminar de Cloudinary + BD (ADMIN/GESTOR_STOCK)

**Características:**
- Upload firmado en backend (no expone credenciales)
- Validación MIME (jpg, png, webp)
- Límite de tamaño: 5MB
- Carpetas configurables (productos, categorias)
- Transformaciones automáticas (f_auto, q_auto, c_fill)
- Sincronización bidireccional con Cloudinary
- Imágenes por producto almacenadas como array de URLs

#### **4.2.7 Admin (Dashboard y Configuración)**

**Propósito:** KPIs, estadísticas y configuración operativa

**Router base:** `/api/v1/admin`

**Dashboard (`/admin/dashboard`):**
- `GET /admin/dashboard` - Datos completos: KPIs + gráficos (ADMIN/GESTOR_STOCK/GESTOR_PEDIDOS)
- `GET /admin/dashboard/productos-mas-vendidos` - Top productos últimos 30 días
- `GET /admin/dashboard/ingresos-mensuales` - Ingresos por mes (últimos 12)
- `GET /admin/dashboard/rentabilidad` - Margen y ganancia por producto

**Configuración (`/admin/configuracion`):**
- `GET /admin/configuracion/costo-envio` - Obtener costo de envío delivery
- `PATCH /admin/configuracion/costo-envio` - Actualizar costo de envío (en memoria, ADMIN/GESTOR_PEDIDOS)

**Características:**
- **Costo de envío configurable en runtime** (almacenado en memoria, se resetea al reiniciar)
- Agregaciones SQL sobre Pedido, DetallePedido y Producto
- Rentabilidad: margen (%) y ganancia ($) por producto activo
- Exclusión de pedidos CANCELADO en todas las estadísticas

#### **4.2.8 WebSocket (Comunicación Tiempo Real)**

**Propósito:** Notificaciones bidireccionales en tiempo real

**Endpoint:**
- `WS /api/v1/ws/pedidos?token=<JWT>` - Conexión autenticada

**Arquitectura de Salas (Rooms):**
- Sala global: `staff:pedidos` (roles: ADMIN, GESTOR_PEDIDOS, CAJERO, COCINA)
- Sala privada: `user:{usuario_id}` (cada cliente ve solo sus pedidos)

**Eventos del Servidor:**
- `hello` - Bienvenida tras conexión exitosa
- `pedido.creado` → sala `staff:pedidos`
- `pedido.estado.cambiado` → sala `staff:pedidos` (pedido completo + historial)
- `pedido.mio.actualizado` → sala `user:{id}` (subset mínimo para cliente)
- `stock.alerta` → sala `staff:pedidos` (ingredientes bajo stock de seguridad)
- `error` - Mensaje de error

**Mensajes del Cliente:**
- `ping` → responde con `pong`
- `subscribe` → reservado para futuro (hoy no se usa)

---

## 5. FRONTEND - ESTRUCTURA Y COMPONENTES

### 5.1 Estructura de Carpetas

```
food-store-frontend/
├── src/
│   ├── app/
│   │   └── router/
│   │       └── ProtectedRoute.tsx  # HOC de protección por roles
│   ├── pages/
│   │   ├── Home.tsx                # Landing page pública
│   │   ├── Checkout.tsx             # MercadoPago + Efectivo
│   │   ├── PedidoExitoso.tsx        # Confirmación con timeline
│   │   ├── auth/
│   │   │   ├── Login.tsx
│   │   │   └── Register.tsx
│   │   ├── client/
│   │   │   ├── MiPerfil.tsx        # Perfil y cambiar contraseña
│   │   │   └── MisPedidos.tsx     # Historial con timeline WS
│   │   ├── admin/
│   │   │   ├── Dashboard.tsx       # KPIs y gráficos
│   │   │   ├── ProductosAdmin.tsx
│   │   │   ├── CategoriasAdmin.tsx
│   │   │   ├── IngredientesAdmin.tsx
│   │   │   ├── GestorPedidos.tsx   # Tabla FSM
│   │   │   ├── VistaCocina.tsx     # KDS
│   │   │   ├── VistaCajero.tsx     # Caja
│   │   │   ├── PanelUsuarios.tsx
│   │   │   └── MotivoModal.tsx     # Modal de cancelación
│   │   └── direcciones/
│   │       └── MisDirecciones.tsx
│   ├── components/
│   │   ├── layout/
│   │   │   ├── AdminLayout.tsx     # Layout admin con sidebar
│   │   │   ├── CartDrawer.tsx     # Carrito deslizable
│   │   │   ├── Layout.tsx         # Layout público
│   │   │   ├── Navbar.tsx         # Navegación
│   │   │   └── ThemeToggle.tsx    # Modo oscuro/claro
│   │   ├── admin/
│   │   │   ├── CategoriaModal.tsx
│   │   │   ├── ImagePicker.tsx
│   │   │   ├── ImageUploader.tsx
│   │   │   ├── IngredienteModal.tsx
│   │   │   └── ProductoModal.tsx
│   │   ├── client/
│   │   │   └── PersonalizarModal.tsx # Personalización de producto
│   │   └── common/
│   │       ├── EmptyState.tsx
│   │       ├── ProductCard.tsx
│   │       └── SkeletonCard.tsx
│   ├── store/
│   │   ├── authStore.ts           # Auth state (persist)
│   │   ├── cartStore.ts           # Carrito (persist)
│   │   ├── pedidoStore.ts         # Pedido actual
│   │   ├── themeStore.ts          # Tema (persist)
│   │   └── wsStore.ts             # WebSocket status
│   ├── services/
│   │   ├── auth.service.ts
│   │   ├── catalogo.service.ts
│   │   ├── pedido.service.ts
│   │   ├── pagos.service.ts
│   │   ├── usuario.service.ts
│   │   ├── direccion.service.ts
│   │   ├── dashboard.service.ts
│   │   ├── configuracion.service.ts  # Costo de envío
│   │   ├── uploads.service.ts
│   │   ├── websocket.service.ts
│   │   └── fallbackPolling.service.ts
│   ├── hooks/
│   │   ├── useRole.ts              # Check permisos
│   │   └── usePedidoWebSocket.ts  # Timeline WS
│   ├── config/
│   │   └── axios.ts               # Cliente HTTP
│   ├── types/
│   │   ├── auth.type.ts
│   │   ├── categoria.type.ts
│   │   ├── dashboard.type.ts
│   │   ├── direccion.type.ts
│   │   ├── ingrediente.type.ts
│   │   ├── pago.type.ts
│   │   ├── pedido.type.ts
│   │   └── producto.type.ts
│   ├── styles/
│   │   ├── admin.css
│   │   └── index.css
│   ├── App.tsx                    # Router principal
│   └── main.tsx
├── public/
├── index.html
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.js
├── postcss.config.js
├── package.json
└── eslint.config.js
```

### 5.2 Gestión de Estado (Zustand Stores)

| Store | Archivo | Propósito | Persistencia |
|-------|---------|----------|--------------|
| **authStore** | `store/authStore.ts` | Usuario, tokens, isAuthenticated | ✅ localStorage |
| **cartStore** | `store/cartStore.ts` | Items del carrito | ✅ localStorage |
| **pedidoStore** | `store/pedidoStore.ts` | Pedido actual en checkout | ❌ No persiste |
| **themeStore** | `store/themeStore.ts` | Modo oscuro/claro | ✅ localStorage |
| **wsStore** | `store/wsStore.ts` | Estado WebSocket | ❌ No persiste |

### 5.3 Rutas de la Aplicación

**Rutas Públicas (Cliente):**
- `/` - Home
- `/login` - Login
- `/registro` - Registro
- `/checkout` - Checkout
- `/pedido-exitoso/:pedidoId` - Confirmación de pedido
- `/mis-pedidos` - Historial de pedidos
- `/mi-perfil` - Perfil del usuario
- `/mis-direcciones` - Gestión de direcciones
- `/carrito` - Carrito (en construcción)

**Rutas Protegidas (Admin/Staff):**
- `/admin` - Redirección según rol
- `/admin/productos` - Gestión de productos
- `/admin/categorias` - Gestión de categorías
- `/admin/ingredientes` - Gestión de ingredientes
- `/admin/pedidos` - Gestor de pedidos (FSM)
- `/admin/cocina` - Vista cocina (KDS)
- `/admin/cajero` - Vista cajero
- `/admin/usuarios` - Panel de usuarios

**Redirección por Rol en Admin:**
- COCINA → `/admin/cocina`
- CAJERO → `/admin/cajero`
- GESTOR_STOCK → `/admin/productos`
- ADMIN/GESTOR_PEDIDOS → Dashboard

---

## 6. MODELO DE DATOS

### 6.1 Entidades Principales

#### **Usuario**
```
id, email (UNIQUE), password (hash bcrypt), nombre, apellido, celular
activo, rol (JSON array de códigos), creado_en, actualizado_en
eliminado_en (soft delete)
```

#### **Rol** (valores permitidos en `rol`)
```
ADMIN, CLIENTE, GESTOR_STOCK, GESTOR_PEDIDOS, CAJERO, COCINA
```

#### **Pedido**
```
id, usuario_id, direccion_id, estado_codigo (FSM)
forma_pago, tipo_entrega (DELIVERY/EN_LOCAL)
subtotal, descuento, costo_envio, total
creado_en, actualizado_en
```

#### **DetallePedido**
```
id, pedido_id, producto_id
cantidad, precio_snapshot, subtotal_snap
nombre_snapshot (nombre del producto al momento)
personalizacion (JSON array de strings)
creado_en
```

#### **HistorialEstadoPedido** (Append-only)
```
id, pedido_id, estado_desde (nullable), estado_hacia
usuario_id, motivo (nullable), creado_en
```

#### **Producto**
```
id, nombre, descripcion
imagenes_url (JSON array de URLs)
stock_cantidad, activo
costo_produccion (calculado desde escandallo)
margen_ganancia, precio
creado_en, actualizado_en, eliminado_en
```

#### **ProductoIngrediente**
```
producto_id, ingrediente_id
cantidad_requerida, es_removible
```

#### **Categoria**
```
id, nombre, descripcion, activo
imagen_url, parent_id (FK a sí misma, opcional)
creado_en, actualizado_en, eliminado_en
```

#### **Ingrediente**
```
id, nombre, disponible, es_alergeno
stock, stock_seguridad, unidad, costo_unitario
creado_en, actualizado_en, eliminado_en
```

#### **Pago**
```
id, pedido_id, mp_payment_id, mp_status
mp_status_detail, transaction_amount
payment_method_id, external_reference
idempotency_key (UNIQUE), preference_id
init_point, creado_en, actualizado_en
```

#### **DireccionEntrega**
```
id, usuario_id, alias, calle, numero
piso, depto, ciudad, provincia, codigo_postal
referencia, es_principal
creado_en, actualizado_en, eliminado_en
```

#### **Imagen**
```
id, public_id (Cloudinary), url, secure_url
formato, ancho, alto, bytes
folder, recurso_tipo
nombre_archivo, subido_por_id
creado_en, eliminado_en
```

---

## 7. API REST - ENDPOINTS

### 7.1 Prefijo y Configuración

- **Base URL:** `/api/v1`
- **Documentación:** `/api/v1/docs` (Swagger UI)
- **Error Format:** RFC 7807 (Problem Details)
- **Authentication:** Bearer token en header `Authorization`

### 7.2 Resumen de Endpoints

| Módulo | Método | Ruta | Rol | Descripción |
|--------|--------|------|-----|-------------|
| **USUARIOS** | POST | `/usuarios/registro` | Público | Registro de usuario |
|  | POST | `/usuarios/login` | Público | Login (OAuth2 form) |
|  | POST | `/usuarios/logout` | Bearer | Logout (revoca refresh) |
|  | POST | `/usuarios/refresh` | Público | Refresco de token (cookie) |
|  | GET | `/usuarios/me` | Bearer | Perfil propio |
|  | PATCH | `/usuarios/me` | Bearer | Actualizar perfil propio |
|  | POST | `/usuarios/me/cambiar-password` | Bearer | Cambiar contraseña |
|  | GET | `/usuarios` | ADMIN | Listar activos (pagin.) |
|  | GET | `/usuarios/gestion` | ADMIN | Listar todos |
|  | GET | `/usuarios/{id}` | ADMIN | Detalle de usuario |
|  | PATCH | `/usuarios/{id}` | ADMIN | Editar usuario |
|  | PATCH | `/usuarios/{id}/roles` | ADMIN | Asignar roles |
|  | DELETE | `/usuarios/{id}` | ADMIN | Soft delete |
|  | PATCH | `/usuarios/{id}/reactivar` | ADMIN | Reactivar |
| **DIRECCIONES** | GET | `/direcciones` | Bearer | Listar propias |
|  | POST | `/direcciones` | Bearer | Crear dirección |
|  | GET | `/direcciones/{id}` | Bearer | Obtener dirección |
|  | PATCH | `/direcciones/{id}` | Bearer | Editar dirección |
|  | PATCH | `/direcciones/{id}/principal` | Bearer | Marcar principal |
|  | DELETE | `/direcciones/{id}` | Bearer | Eliminar (soft) |
|  | PATCH | `/direcciones/{id}/reactivar` | Bearer | Reactivar |
| **CATÁLOGO** | GET | `/catalogo/categorias` | Público | Listar categorías |
|  | POST | `/catalogo/categorias` | ADMIN/GESTOR_STOCK | Crear categoría |
|  | GET | `/catalogo/categorias/{id}` | Público | Detalle categoría |
|  | PATCH | `/catalogo/categorias/{id}` | ADMIN/GESTOR_STOCK | Editar categoría |
|  | PATCH | `/catalogo/categorias/{id}/visibilidad` | ADMIN/GESTOR_STOCK | Toggle activo |
|  | PATCH | `/catalogo/categorias/{id}/reactivar` | ADMIN/GESTOR_STOCK | Reactivar |
|  | DELETE | `/catalogo/categorias/{id}` | ADMIN/GESTOR_STOCK | Soft delete |
|  | GET | `/catalogo/productos` | Público | Listar productos |
|  | POST | `/catalogo/productos` | ADMIN/GESTOR_STOCK | Crear (escandallo) |
|  | GET | `/catalogo/productos/{id}` | Público | Detalle con receta |
|  | PATCH | `/catalogo/productos/{id}` | ADMIN/GESTOR_STOCK | Editar |
|  | PATCH | `/catalogo/productos/{id}/disponibilidad` | ADMIN/GESTOR_STOCK | Toggle |
|  | PATCH | `/catalogo/productos/{id}/imagenes` | ADMIN/GESTOR_STOCK | Actualizar imgs |
|  | PATCH | `/catalogo/productos/{id}/reactivar` | ADMIN/GESTOR_STOCK | Reactivar |
|  | DELETE | `/catalogo/productos/{id}` | ADMIN/GESTOR_STOCK | Soft delete |
|  | GET | `/catalogo/ingredientes` | Público | Listar ingredientes |
|  | POST | `/catalogo/ingredientes` | ADMIN/GESTOR_STOCK | Crear ingrediente |
|  | GET | `/catalogo/ingredientes/{id}` | Público | Detalle ingrediente |
|  | PATCH | `/catalogo/ingredientes/{id}` | ADMIN/GESTOR_STOCK | Editar |
|  | PATCH | `/catalogo/ingredientes/{id}/reactivar` | ADMIN/GESTOR_STOCK | Reactivar |
|  | DELETE | `/catalogo/ingredientes/{id}` | ADMIN/GESTOR_STOCK | Soft delete |
| **PEDIDOS** | POST | `/pedidos` | Bearer | Crear pedido (UoW) |
|  | GET | `/pedidos` | Bearer | Listar (propios/staff) |
|  | GET | `/pedidos/{id}` | Propietario/Staff | Detalle + historial |
|  | GET | `/pedidos/{id}/historial` | Propietario/Staff | Historial estados |
|  | PATCH | `/pedidos/{id}/estado` | Staff | Avanzar FSM |
|  | PATCH | `/pedidos/{id}/cancelar` | Bearer | Cancelar con motivo |
|  | GET | `/pedidos/admin` | Staff | Lista enriquecida |
|  | GET | `/pedidos/gestion/todos` | Staff | Lista completa |
| **PAGOS** | POST | `/pagos/crear` | Bearer | Crear preference MP |
|  | POST | `/pagos/webhook` | Público | Webhook IPN MP |
|  | GET | `/pagos/redirect/success` | Público | Redir. aprobación |
|  | GET | `/pagos/redirect/failure` | Público | Redir. rechazo |
|  | GET | `/pagos/redirect/pending` | Público | Redir. pendiente |
|  | GET | `/pagos/{pedido_id}` | Propietario/Staff | Consultar pago |
|  | POST | `/pagos/{pedido_id}/sincronizar` | Staff | Sync manual MP |
| **IMÁGENES** | POST | `/imagenes/upload` | ADMIN/GESTOR_STOCK | Upload Cloudinary |
|  | GET | `/imagenes` | ADMIN/GESTOR_STOCK | Listar (paginado) |
|  | GET | `/imagenes/{id}` | ADMIN/GESTOR_STOCK | Detalle imagen |
|  | POST | `/imagenes/sincronizar` | ADMIN/GESTOR_STOCK | Sync con Cloud. |
|  | DELETE | `/imagenes/{id}` | ADMIN/GESTOR_STOCK | Eliminar registro |
|  | DELETE | `/imagenes/cloudinary/{public_id}` | ADMIN/GESTOR_STOCK | Eliminar Cloud. |
| **ADMIN** | GET | `/admin/dashboard` | Staff | KPIs + gráficos |
|  | GET | `/admin/dashboard/productos-mas-vendidos` | Staff | Top productos |
|  | GET | `/admin/dashboard/ingresos-mensuales` | Staff | Ingresos por mes |
|  | GET | `/admin/dashboard/rentabilidad` | Staff | Rentabilidad |
|  | GET | `/admin/configuracion/costo-envio` | Staff | Obtener costo envío |
|  | PATCH | `/admin/configuracion/costo-envio` | ADMIN/GESTOR_PEDIDOS | Actualizar costo |
| **WEBSOCKET** | WS | `/ws/pedidos?token=<jwt>` | Bearer | Feed tiempo real |

---

## 8. SISTEMA DE SEGURIDAD Y RBAC

### 8.1 Autenticación (JWT + Cookies HttpOnly)

**Flujo:**
1. Usuario envía credenciales a `/usuarios/login` (OAuth2PasswordRequestForm)
2. Backend valida contraseña (bcrypt) y genera JWTs
3. **Access Token:** 30 minutos (devuelto en JSON)
4. **Refresh Token:** 7 días (en cookie HttpOnly)
5. Frontend almacena access_token en localStorage
6. Refresh token回転 en cookie automáticamente
7. En cada request: `Authorization: Bearer <access_token>`

**Componentes:**
- `python-jose` para generación/validación de JWT
- `bcrypt` para hashing de contraseñas
- Cookies HttpOnly para refresh token (seguro contra XSS)
- Rate limiting 5/15 min en login/register

### 8.2 RBAC (Role-Based Access Control)

#### **6 Roles Implementados**

| Rol | Código | Responsabilidades |
|-----|--------|------------------|
| **Administrador** | ADMIN | Control total: CRUD todo, estadísticas, usuarios, configuración |
| **Cliente Tienda** | CLIENTE | Comprar, perfil, pedidos propios, direcciones |
| **Gestor de Stock** | GESTOR_STOCK | Productos, categorías, ingredientes, imágenes |
| **Gestor de Pedidos** | GESTOR_PEDIDOS | Avanzar pedidos, ver todos, configurar costo envío |
| **Cajero** | CAJERO | Confirmar pagos, crear pedidos, ver pedidos, sincronizar pagos |
| **Cocina** | COCINA | Ver pedidos, avanzar EN_PREPARACION→ENTREGADO |

#### **Matriz de Permisos**

| Permiso | ADMIN | CLIENTE | GESTOR_STOCK | GESTOR_PEDIDOS | CAJERO | COCINA |
|---------|-------|---------|--------------|----------------|--------|--------|
| Ver catálogo | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Gestionar productos | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| Gestionar categorías | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| Gestionar ingredientes | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| Crear pedido | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ |
| Ver pedidos propios | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ |
| Gestionar pedidos | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ |
| Ver perfil propio | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Gestionar usuarios | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Gestionar direcciones | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Gestionar imágenes | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| Ver dashboard | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ |
| Configurar costo envío | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ |
| Sincronizar pagos | ✅ | ❌ | ❌ | ✅ | ✅ | ❌ |

### 8.3 Protección CORS

```python
CORSMiddleware(
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 8.4 Rate Limiting

- **Límite:** 5 intentos fallidos
- **Ventana:** 15 minutos
- **Middleware:** `RateLimitMiddleware` (personalizado)
- **Respuesta:** HTTP 429 + header `Retry-After`

---

## 9. INTEGRACIONES EXTERNAS

### 9.1 MercadoPago

#### **Configuración**

```python
MP_ACCESS_TOKEN = "..."
MP_PUBLIC_KEY = "..."
MP_NOTIFICATION_URL = "http://localhost:8000/api/v1/pagos/webhook"
MP_WEBHOOK_SECRET = "..."  # Para validar firma HMAC-SHA256
FRONTEND_URL = "http://localhost:5173"
```

#### **Flujo de Pago Completo**

1. **Frontend:** Cliente selecciona productos y completa checkout
2. **Frontend → Backend:** `POST /pagos/crear` con `pedido_id`
3. **Backend:** Genera preference con MercadoPago SDK
4. **Backend:** Retorna `init_point` (URL de pago MP)
5. **Frontend:** Redirige a `init_point` (MercadoPago checkout)
6. **Post-pago:** MP redirige a `/pagos/redirect/{status}?pedido_id=X`
7. **Backend:** Redirige a `/pedido-exitoso/{id}?status=X`
8. **Webhook:** MP envía notificación IPN al backend (validación HMAC)
9. **Backend:** Actualiza estado pedido/pago
10. **WebSocket:** Notifica al cliente en tiempo real

#### **Estados de Pago**

```
pending → approved / rejected / voided
```

#### **Seguridad**

- ✅ Validación de firma HMAC-SHA256 en webhook (`MP_WEBHOOK_SECRET`)
- ✅ Idempotency keys para evitar cobros duplicados
- ✅ Redirecciones firmadas para flujo completo

### 9.2 Cloudinary

#### **Configuración**

```python
CLOUDINARY_CLOUD_NAME = "..."
CLOUDINARY_API_KEY = "..."
CLOUDINARY_API_SECRET = "..."
CLOUDINARY_FOLDER = "foodstore"
CLOUDINARY_MAX_FILE_MB = 5
```

#### **Características**

- **Upload:** Backend-signed (SDK Python, no expone credenciales)
- **Folders:** `foodstore/productos`, `foodstore/categorias`
- **Formatos:** jpg, jpeg, png, webp
- **Límite:** 5MB por archivo
- **Transformaciones:** f_auto, q_auto, c_fill
- **Sincronización:** BD ↔ Cloudinary bidireccional

### 9.3 PostgreSQL

- **Versión:** 15+
- **Driver:** psycopg2-binary
- **Conexión:** SQLModel/SQLAlchemy pool
- **Migraciones:** Alembic

---

## 10. WEBSOCKETS - COMUNICACIÓN TIEMPO REAL

### 10.1 Arquitectura

#### **WSManager (`app/modules/pedido/ws_manager.py`)**

Gestor de conexiones en memoria con soporte para salas (rooms):

```python
class ConnectionManager:
    async def connect(websocket, usuario_id, rooms)
    async def disconnect(websocket)
    async def join_room(websocket, room)
    async def leave_room(websocket, room)
    async def broadcast(room, event) -> int  # Retorna cantidad de recipients
    async def send_personal(websocket, event) -> bool
```

**Salas:**
- `staff:pedidos` — Todos los pedidos (staff only)
- `user:{usuario_id}` — Pedidos propios (cliente)

### 10.2 Autenticación JWT en Handshake

```python
# Validación ANTES de websocket.accept() (Unidad 5)
try:
    user = decode_access_token(token)
except JWTError:
    return  # Cierra sin accept → 403
await websocket.accept()
await ws_manager.connect(websocket, usuario_id, rooms)
```

### 10.3 Estructura de Eventos

```json
// Servidor → Cliente
{
  "type": "hello",
  "payload": { "usuario_id": 5, "rooms": ["user:5", "staff:pedidos"], "server_ts": ... }
}

// Servidor → Cliente (cliente)
{
  "type": "pedido.mio.actualizado",
  "payload": { "id": 42, "estado_codigo": "CONFIRMADO", "actualizado_en": "..." }
}

// Servidor → Staff
{
  "type": "pedido.estado.cambiado",
  "payload": { "pedido": {...}, "estado_desde": "...", "estado_hacia": "...", "historial": {...} }
}

// Servidor → Staff
{
  "type": "stock.alerta",
  "payload": { "ingredientes_criticos": [...], "total": 3 }
}
```

```json
// Cliente → Servidor
{ "type": "ping" }  // → Responde con { "type": "pong", "payload": { "t": ... } }
```

### 10.4 Hooks Frontend

```typescript
const { estado, historial, conexionActiva } = usePedidoWebSocket(pedido_id);
```

---

## 11. TESTING Y QA

### 11.1 Estructura de Tests

```
foood-store-backend/tests/
├── conftest.py              # Fixtures compartidos
├── unit/
│   ├── test_pagos_crear.py  # Unit tests de pagos
│   ├── test_pedido_fsm.py   # Unit tests de FSM
│   └── test_pedido_schemas.py # Unit tests de schemas
└── integration/
    ├── test_auth.py               # Tests de autenticación
    ├── test_pagos_sincronizar.py  # Tests de sincronización MP
    ├── test_pagos_webhook.py      # Tests de webhook
    ├── test_pedido_crud.py        # Tests CRUD pedidos
    └── test_pedido_estado.py      # Tests de transición de estados
```

### 11.2 Fixtures Principales (conftest.py)

| Fixture | Scope | Descripción |
|---------|-------|-------------|
| `engine` | session | Motor SQLite in-memory |
| `db_session` | function | Sesión limpia con rollback |
| `client` | function | TestClient FastAPI |
| `admin_headers` | function | Token ADMIN |
| `client_headers` | function | Token CLIENTE |
| `pedidos_headers` | function | Token GESTOR_PEDIDOS |

### 11.3 Ejecución de Tests

```bash
# Ejecutar todos los tests
pytest

# Con cobertura
pytest --cov=app --cov-report=html

# Tests unitarios
pytest tests/unit/ -v

# Tests de integración
pytest tests/integration/ -v

# Tests específicos
pytest tests/integration/test_auth.py -v
```

---

## 12. GESTIÓN DE ARCHIVOS Y MEDIOS

### 12.1 Upload de Imágenes

#### **Flujo**

1. **Frontend:** Selecciona archivo (jpg, png, webp, ≤5MB)
2. **Frontend → Backend:** `POST /api/v1/imagenes/upload`
3. **Backend:** Genera firma Cloudinary (backend-signed)
4. **Backend → Cloudinary:** Upload firmado
5. **Cloudinary:** Retorna public_id y URLs
6. **Backend → DB:** Registro en tabla Imagen
7. **Backend → Frontend:** Retorna metadatos

#### **Validaciones**

- MIME types: jpg, jpeg, png, webp
- Tamaño máximo: 5MB (configurable en `CLOUDINARY_MAX_FILE_MB`)
- Carpeta: configurable (por defecto `foodstore/productos`)
- Unique filename para evitar sobreescrituras

### 12.2 Sincronización BD ↔ Cloudinary

- `POST /imagenes/sincronizar?folder=productos` reconcilia la tabla local con Cloudinary
- Crea filas para imágenes nuevas en Cloudinary
- Marca como eliminadas las filas huérfanas

---

## RESUMEN TÉCNICO

### Tecnologías Principales

- **Backend:** FastAPI + SQLModel + PostgreSQL
- **Frontend:** React + TypeScript + Tailwind CSS + Vite
- **Tiempo Real:** WebSockets con JWT + Rooms (staff + usuario)
- **Pagos:** MercadoPago Checkout PRO con webhook HMAC
- **Medios:** Cloudinary con sincronización bidireccional
- **Testing:** pytest + pytest-asyncio + httpx

### Características Clave

✅ **RBAC completo** (6 roles con permisos granulares)
✅ **FSM para pedidos** (6 estados validados)
✅ **Unit of Work** (transacciones atómicas)
✅ **WebSockets con Rooms** (staff global + usuario privado)
✅ **MercadoPago** (checkout PRO + webhook HMAC + sync manual)
✅ **Cloudinary** (upload firmado + sincronización)
✅ **Stock de seguridad** (alertas WebSocket por ingrediente)
✅ **Escandallo automático** (costo_produccion desde ingredientes)
✅ **Soft delete + Reactivación** (en todas las entidades)
✅ **Costo de envío configurable** (en runtime)
✅ **20+ tests** (unit + integration con pytest)
✅ **40+ endpoints REST** (documentados en Swagger)
✅ **Cookies HttpOnly** (refresh token seguro)
✅ **Rate limiting** (protección contra brute force)
