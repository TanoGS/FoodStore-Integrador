## INFORME
#  TPI Programación IV — UTN

**Integrantes:** Renzo Sosa, Sponton Giani

---

##  TABLA DE CONTENIDOS

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
| **PyJWT** | (últimas) | Generación y validación de JWT |
| **python-cloudinary** | (últimas) | Cliente de Cloudinary |
| **mercadopago** | 2.3.0 | SDK de MercadoPago |
| **python-dotenv** | (últimas) | Gestión de variables de entorno |
| **uvicorn** | (últimas) | Servidor ASGI |
| **pytest** | (últimas) | Framework de testing |

### 2.2 Frontend

| Componente | Versión | Propósito |
|-----------|---------|----------|
| **React** | 19.2.4 | Librería UI y gestión de componentes |
| **TypeScript** | 6.0.2 | Tipado estático para JavaScript |
| **Vite** | 8.0.4 | Build tool y dev server |
| **React Router DOM** | 7.14.1 | Enrutamiento en SPA |
| **Tailwind CSS** | 4.2.2 | Framework CSS utility-first |
| **TanStack Query** | 5.99.0 | Gestión de estado asincrónico (servidor) |
| **TanStack Form** | 1.29.0 | Gestión avanzada de formularios |
| **Zustand** | 5.0.12 | Gestión de estado global ligera |
| **Axios** | 1.15.0 | Cliente HTTP |
| **Recharts** | 3.8.1 | Librería de gráficos |
| **Lucide React** | 1.11.0 | Iconografía SVG |
| **@mercadopago/sdk-react** | (últimas) | SDK de MercadoPago para React |

### 2.3 Herramientas DevOps y Testing

| Herramienta | Propósito |
|-----------|----------|
| **Alembic** | Control de versiones de esquema BD |
| **Docker** | Containerización (opcional) |
| **pytest** | Testing unitario e integración |
| **ESLint** | Linting de código JavaScript |
| **PostCSS** | Procesamiento de CSS |
| **Git** | Control de versiones |

---

## 3. ARQUITECTURA GENERAL

### 3.1 Diagrama de Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React + Vite)                  │
├─────────────────────────────────────────────────────────────────┤
│  Pages (Home, Menu, Checkout, Dashboard, Admin)                 │
│  Components (Layout, Client, Admin, Common)                     │
│  Stores (Zustand) → Auth, Cart, Theme, WebSocket                │
│  Services (Axios) → API calls                                   │
│  Hooks → useRole, usePedidoWebSocket, useAdminOrdersFeed        │
└─────────────┬──────────────────────────┬────────────────────────┘
              │ HTTP/REST + WebSocket    │
              │ (Token JWT en headers)   │
              │                          │
┌─────────────▼──────────────────────────▼────────────────────────┐
│                    BACKEND GATEWAY (FastAPI)                    │
├─────────────────────────────────────────────────────────────────┤
│  CORS | Rate Limiting | Auth Middleware | Request/Response      │
└──────────┬────────────────────────────┬──────────────────────────┘
           │                            │
    ┌──────▼────────────┐       ┌──────▼──────────┐
    │   REST API        │       │  WebSocket      │
    │   (/api/v1)       │       │  Manager        │
    │                   │       │  (/ws/pedidos)  │
    │ Modules:          │       │                 │
    │ - Auth            │       │ Features:       │
    │ - Usuarios        │       │ - Broadcast     │
    │ - Pedidos         │       │ - Auth JWT      │
    │ - Pagos           │       │ - Pool conex.   │
    │ - Catálogo        │       └─────────────────┘
    │ - Direcciones     │
    │ - Admin           │
    │ - Imagenes        │
    └──────┬────────────┘
           │
┌──────────▼────────────────────────────────────────────────────┐
│           SERVICE LAYER (Business Logic)                      │
├────────────────────────────────────────────────────────────┤
│ - AuthService         - ProductoService                   │
│ - UsuarioService      - PedidoService (FSM + UoW)         │
│ - PagoService         - EstadisticasService               │
│ - DirectionService    - ImagenService (Cloudinary)        │
└──────────┬─────────────────────────────────────────────────┘
           │
┌──────────▼────────────────────────────────────────────────────┐
│        DATA ACCESS LAYER (Repository + UoW)                   │
├────────────────────────────────────────────────────────────┤
│ - GenericRepository                                        │
│ - UnitOfWork (transacciones atómicas)                      │
│ - Query builders                                           │
└──────────┬─────────────────────────────────────────────────┘
           │
  ┌────────▼──────────┬──────────────┬──────────────┐
  │                   │              │              │
  ▼                   ▼              ▼              ▼
PostgreSQL      MercadoPago     Cloudinary    Otros servicios
(BD principal)  (Pagos)         (Imágenes)
```

### 3.2 Patrones de Arquitectura

| Patrón | Implementación | Beneficio |
|--------|----------------|-----------|
| **Feature-First** | Módulos organizados por dominio (auth, pedido, etc.) | Escalabilidad, mantenibilidad |
| **Repository Pattern** | GenericRepository + UnitOfWork | Desacoplamiento, testabilidad |
| **Unit of Work** | Transacciones atómicas en pedidos | Consistencia de datos |
| **FSM (Finite State Machine)** | Estados de pedido con reglas validadas | Flujo de negocio claro |
| **Dependency Injection** | FastAPI dependencies | Flexibilidad, testing |
| **JWT-based Auth** | Tokens access + refresh | Seguridad stateless |
| **RBAC (Role-Based Access Control)** | 6 roles con 11 permisos | Control granular de acceso |
| **WebSocket Manager** | Pool singleton con canales | Comunicación bidireccional |
| **Cloudinary Integration** | Backend-signed uploads | Seguridad en manejo de medios |

---

## 4. MÓDULOS DEL BACKEND

### 4.1 Estructura de Carpetas

```
foood-store-backend/
├── app/
│   ├── modules/
│   │   ├── auth/              # Autenticación y autorización
│   │   ├── usuario/           # Gestión de usuarios
│   │   ├── direccion/         # Direcciones de entrega
│   │   ├── catalogo/          # Productos e ingredientes
│   │   │   ├── categoria/
│   │   │   └── producto/
│   │   ├── pedido/            # Dominio central (FSM, UoW)
│   │   ├── pagos/             # Integración MercadoPago
│   │   ├── imagenes/          # Uploads Cloudinary
│   │   └── admin/             # Dashboard y estadísticas
│   └── core/
│       ├── config.py          # Variables de entorno
│       ├── database.py        # Conexión y sesión
│       ├── security.py        # JWT, contraseñas, CORS
│       ├── repository.py      # GenericRepository
│       ├── unit_of_work.py    # Transacciones
│       └── ws_manager.py      # WebSocket Manager
├── alembic/                   # Migraciones de BD
├── tests/                     # Suite de tests
├── main.py                    # Punto de entrada
└── requirements.txt           # Dependencias Python
```

### 4.2 Módulos Implementados (11)

#### **4.2.1 Auth (Autenticación)**

**Propósito:** Gestionar login, registro, refresh de tokens y logout

**Endpoints:**
- `POST /api/v1/auth/register` - Registro de nuevo usuario
- `POST /api/v1/auth/login` - Autenticación (rate limited 5/15 min)
- `POST /api/v1/auth/refresh` - Renovación de access token
- `POST /api/v1/auth/logout` - Cierre de sesión y revocación
- `GET /api/v1/auth/me` - Perfil del usuario autenticado

**Tecnología:**
- Contraseñas hasheadas con bcrypt
- JWT access token: 30 minutos
- JWT refresh token: 7 días
- Rate limiting: 5 intentos fallidos en 15 minutos

#### **4.2.2 Usuarios (Gestión de usuarios)**

**Propósito:** CRUD de usuarios y asignación de roles

**Endpoints:**
- `GET /api/v1/usuarios` - Listar usuarios (admin)
- `GET /api/v1/usuarios/{id}` - Detalle de usuario
- `PUT /api/v1/usuarios/{id}` - Editar datos de usuario
- `DELETE /api/v1/usuarios/{id}` - Soft delete

**Características:**
- Soft delete (no eliminación física)
- Asignación de roles dinámicos
- Auditoría de cambios

#### **4.2.3 Direcciones (Gestión de direcciones)**

**Propósito:** CRUD completo de direcciones de entrega por usuario

**Endpoints:**
- `GET /api/v1/direcciones` - Listar direcciones del usuario
- `POST /api/v1/direcciones` - Crear nueva dirección
- `PUT /api/v1/direcciones/{id}` - Editar dirección
- `DELETE /api/v1/direcciones/{id}` - Eliminar dirección
- `PATCH /api/v1/direcciones/{id}/principal` - Marcar como principal

**Características:**
- Una dirección principal por usuario
- Campos de geolocalización (calle, número, piso, ciudad, provincia, CP)
- Referencias personalizadas

#### **4.2.4 Catálogo (Productos y Categorías)**

**Propósito:** Gestión del catálogo de productos e ingredientes

**Sub-módulos:**
- **Categorías:** CRUD jerárquico con soporte para subcategorías
- **Productos:** Asociación con categorías, ingredientes y stock
- **Ingredientes:** Gestión de componentes con control de alérgenos

**Endpoints:**
- `GET /api/v1/categorias` - Listar categorías (árbol)
- `POST/PUT/DELETE /api/v1/categorias/{id}` - CRUD categorías
- `GET /api/v1/productos` - Listar con filtros y paginación
- `GET/POST/PUT/DELETE /api/v1/productos/{id}` - CRUD productos
- `GET /api/v1/ingredientes` - Listar ingredientes

**Características:**
- Categorías jerárquicas (parent_id)
- Stock dinámico
- Imágenes con Cloudinary
- Compatibilidad de ingredientes

#### **4.2.5 Pedidos (Dominio Central)**

**Propósito:** Gestión completa del ciclo de vida de pedidos con FSM

**Endpoints:**
- `POST /api/v1/pedidos` - Crear pedido (UoW atómico)
- `GET /api/v1/pedidos` - Listar propios o todos (según rol)
- `GET /api/v1/pedidos/{id}` - Detalle con historial
- `PATCH /api/v1/pedidos/{id}/estado` - Avanzar FSM
- `DELETE /api/v1/pedidos/{id}` - Cancelar pedido

**Características:**
- **FSM 6 estados:** PENDIENTE → CONFIRMADO → EN_PREPARACION → EN_CAMINO → ENTREGADO / CANCELADO
- **Validaciones de transición:** Solo transiciones válidas permitidas
- **Historial append-only:** Registro inmutable de cambios de estado
- **Unit of Work:** Transacciones atómicas
- **Snapshots de datos:** Captura de precios históricos
- **Validaciones de stock:** Pre-validación al crear pedido (400) + pre-validación al confirmar (409) + WebSocket `stock.alerta` al staff

**Máquina de Estados:**

| Estado | Orden | Terminal | Puede pasar a |
|--------|-------|----------|---------------|
| PENDIENTE | 1 | No | CONFIRMADO, CANCELADO |
| CONFIRMADO | 2 | No | EN_PREPARACION, CANCELADO |
| EN_PREPARACION | 3 | No | EN_CAMINO, CANCELADO |
| EN_CAMINO | 4 | No | ENTREGADO |
| ENTREGADO | 5 | ✅ Sí | — (terminal) |
| CANCELADO | 6 | ✅ Sí | — (terminal) |

#### **4.2.6 Pagos (Integración MercadoPago)**

**Propósito:** Gestión de pagos online con MercadoPago

**Endpoints:**
- `POST /api/v1/pagos/crear` - Crear pago con token MP
- `POST /api/v1/pagos/webhook` - IPN MercadoPago
- `GET /api/v1/pagos/{pedido_id}` - Consultar pago asociado

**Características:**
- Checkout PRO de MercadoPago
- Tokenización segura de tarjetas
- Webhook IPN para notificaciones
- Idempotency keys UUID
- Estados: pending → approved → rejected

**Formas de pago soportadas:**
-  **MercadoPago:** Para DELIVERY (obligatorio)
-  **Efectivo:** Para EN_LOCAL (pedido queda en PENDIENTE)

#### **4.2.7 Imagenes (Gestión de medios)**

**Propósito:** Upload y eliminación de imágenes con Cloudinary

**Endpoints:**
- `POST /api/v1/imagenes` - Upload de imagen
- `DELETE /api/v1/imagenes/{public_id}` - Eliminar imagen

**Características:**
- Upload firmado en backend (no expone credenciales)
- Validación MIME (jpg, png, webp)
- Límite de tamaño: 5MB
- Almacenamiento en carpetas (foodstore/productos, foodstore/categorias)
- Transformaciones automáticas (f_auto, q_auto, c_fill)

#### **4.2.8 WebSocket (Comunicación Tiempo Real)**

**Propósito:** Notificaciones bidireccionales en tiempo real

**Canales:**
- `/ws/pedidos` - Feed general de pedidos
- Admin channel - Notificaciones administrativas

**Características:**
- Autenticación JWT en handshake
- Pool de conexiones por canal
- Broadcast post-commit (fuera del UoW)
- Reconexión exponencial
- Eventos: pedido.creado, pedido.estado.cambiado, stock.alerta

#### **4.2.9 Admin (Administración)**

**Propósito:** Gestión de usuarios, roles y stock

**Endpoints:**
- `GET /api/v1/admin/usuarios` - Listar usuarios
- `PUT /api/v1/admin/usuarios/{id}/roles` - Asignar rol

**Características:**
- RBAC completo
- Auditoría de cambios
- Gestión de permisos

#### **4.2.10 Estadísticas (Analytics)**

**Propósito:** KPIs y métricas del negocio

**Endpoints:**
- `GET /api/v1/admin/estadisticas/resumen` - KPIs: ventas hoy, ticket promedio
- `GET /api/v1/admin/estadisticas/ventas` - Ventas por período
- `GET /api/v1/admin/estadisticas/productos-top` - Top productos por ingresos
- `GET /api/v1/admin/estadisticas/pedidos-por-estado` - Distribución por estado
- `GET /api/v1/admin/estadisticas/ingresos` - Ingresos por forma de pago

**Características:**
- Agregaciones por período (DIARIO, MENSUAL)
- Snapshot de precios históricos
- Exclusión de pedidos cancelados
- Montos DECIMAL(10,2)

#### **4.2.11 Core (Utilidades principales)**

**Componentes:**

| Archivo | Propósito |
|---------|----------|
| `config.py` | Lectura de variables de entorno (.env) |
| `database.py` | Engine de SQLModel y sesión |
| `security.py` | JWT, bcrypt, CORS |
| `repository.py` | GenericRepository para todas las entidades |
| `unit_of_work.py` | Patrón UoW para transacciones atómicas |
| `ws_manager.py` | Singleton WSManager para WebSockets |

---

## 5. FRONTEND - ESTRUCTURA Y COMPONENTES

### 5.1 Estructura de Carpetas

```
food-store-frontend/
├── src/
│   ├── pages/
│   │   ├── Home.tsx              # Landing page
│   │   ├── Checkout.tsx          # MercadoPago + EFECTIVO
│   │   ├── PedidoExitoso.tsx     # Confirmación con timeline
│   │   ├── auth/
│   │   │   ├── Login.tsx
│   │   │   └── Register.tsx
│   │   ├── client/
│   │   │   ├── Menu.tsx          # Catálogo
│   │   │   ├── Carrito.tsx
│   │   │   ├── MisPedidos.tsx
│   │   │   └── MiPerfil.tsx
│   │   ├── admin/
│   │   │   ├── Dashboard.tsx     # KPIs y gráficos
│   │   │   ├── ProductosAdmin.tsx
│   │   │   ├── CategoriasAdmin.tsx
│   │   │   ├── IngredientesAdmin.tsx
│   │   │   ├── GestorPedidos.tsx
│   │   │   ├── VistaCocina.tsx
│   │   │   ├── VistaCajero.tsx
│   │   │   └── PanelUsuarios.tsx
│   │   └── direcciones/
│   │       └── MisDirecciones.tsx
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Header.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── Footer.tsx
│   │   ├── client/
│   │   │   ├── ProductCard.tsx
│   │   │   ├── CartItem.tsx
│   │   │   └── OrderTimeline.tsx
│   │   ├── admin/
│   │   │   ├── KPICard.tsx
│   │   │   ├── ChartComponent.tsx
│   │   │   ├── OrderManagement.tsx
│   │   │   └── UserManager.tsx
│   │   └── common/
│   │       ├── Button.tsx
│   │       ├── Modal.tsx
│   │       ├── Form.tsx
│   │       └── Toast.tsx
│   ├── store/
│   │   ├── authStore.ts          # Auth state (persist)
│   │   ├── cartStore.ts          # Carrito (persist)
│   │   ├── themeStore.ts         # Tema (persist)
│   │   ├── wsStore.ts            # WebSocket status
│   │   └── uiStore.ts            # UI state
│   ├── services/
│   │   ├── auth.service.ts
│   │   ├── catalogo.service.ts
│   │   ├── pedido.service.ts
│   │   ├── pagos.service.ts
│   │   ├── usuario.service.ts
│   │   ├── direccion.service.ts
│   │   ├── dashboard.service.ts
│   │   ├── uploads.service.ts
│   │   ├── websocket.service.ts
│   │   └── fallbackPolling.service.ts
│   ├── hooks/
│   │   ├── useRole.ts            # Check permisos
│   │   ├── usePedidoWebSocket.ts # Timeline WS
│   │   └── useAdminOrdersFeed.ts # Feed admin WS
│   ├── config/
│   │   └── axios.ts              # Cliente HTTP
│   ├── types/
│   │   ├── producto.type.ts
│   │   ├── categoria.type.ts
│   │   ├── pedido.type.ts
│   │   ├── usuario.type.ts
│   │   ├── dashboard.type.ts
│   │   └── ingrediente.type.ts
│   ├── styles/
│   │   ├── admin.css
│   │   ├── index.css
│   │   └── App.css
│   ├── assets/
│   ├── App.tsx
│   └── main.tsx
├── public/
├── index.html
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.js
└── package.json
```

### 5.2 Gestión de Estado (Zustand Stores)

| Store | Archivo | Propósito | Persistencia |
|-------|---------|----------|--------------|
| **authStore** | `store/authStore.ts` | Usuario, tokens, isAuthenticated | ✅ localStorage |
| **cartStore** | `store/cartStore.ts` | Items del carrito | ✅ localStorage |
| **themeStore** | `store/themeStore.ts` | Modo oscuro/claro | ✅ localStorage |
| **wsStore** | `store/wsStore.ts` | Estado WebSocket | ❌ No persiste |
| **uiStore** | `store/uiStore.ts` | Modales, notificaciones | ❌ No persiste |

### 5.3 Servicios (Axios)

Todos los servicios utilizan Axios con interceptores de autenticación:

| Servicio | Propósito |
|----------|----------|
| `auth.service.ts` | Register, login, refresh, logout, me |
| `catalogo.service.ts` | Listar/crear/editar categorías, productos, ingredientes |
| `pedido.service.ts` | CRUD pedidos, cambio de estado |
| `pagos.service.ts` | Crear pago, obtener estado |
| `usuario.service.ts` | Perfil, editar datos |
| `direccion.service.ts` | CRUD direcciones, marcar principal |
| `dashboard.service.ts` | Obtener KPIs y estadísticas |
| `uploads.service.ts` | Upload/delete imágenes |
| `websocket.service.ts` | Conexión y reconexión WS |
| `fallbackPolling.service.ts` | Fallback si WS falla |

### 5.4 Hooks Personalizados

| Hook | Archivo | Descripción |
|------|---------|-------------|
| `useRole` | `hooks/useRole.ts` | Verificar permisos del usuario |
| `usePedidoWebSocket` | `hooks/usePedidoWebSocket.ts` | Timeline de pedido en tiempo real |
| `useAdminOrdersFeed` | `hooks/useAdminOrdersFeed.ts` | Feed de pedidos para admin |

### 5.5 Páginas Principales

#### **Home**
- Landing page pública
- Links a login/register
- Información del negocio

#### **Auth (Login/Register)**
- Formularios con TanStack Form
- Validación en tiempo real
- Rate limiting visual
- Redirección post-autenticación

#### **Menu (Catálogo)**
- Grid de productos
- Filtros por categoría
- Búsqueda con debounce
- Paginación
- Skeleton loaders
- Agregar al carrito

#### **Carrito**
- Listado de items
- Modificar cantidades
- Eliminar productos
- Subtotal, impuestos, total
- Botón checkout

#### **Checkout**
- Selector de forma de pago:
  -  MercadoPago CardPayment
  -  Efectivo
- Selector de dirección
- Tipo de entrega (EN_LOCAL, DELIVERY)
- MercadoPago Brick integrado

#### **PedidoExitoso**
- Confirmación de compra
- Número de pedido
- Timeline de estado con WS
- Link a "Mis Pedidos"

#### **MisPedidos**
- Historial de pedidos del cliente
- Timeline interactivo con WS
- Estados visuales
- Cancelación (si PENDIENTE/CONFIRMADO)

#### **Dashboard (Admin)**
- 4 KPIs: ventas hoy, ticket promedio, pedidos activos, mes actual
- Gráficos recharts:
  - LineChart: Ventas por período
  - BarChart: Top 5 productos
  - PieChart: Distribución por estado
- Filtros de período (DIARIO, MENSUAL)

#### **Admin - Gestión de Productos**
- CRUD productos
- Upload de imagen (Cloudinary)
- Selector de categorías e ingredientes
- Stock y precios
- Soft delete

#### **Admin - Gestión de Categorías**
- Árbol jerárquico
- CRUD categorías
- Imagen por categoría
- Ordenamiento por parent

#### **Admin - Gestión de Ingredientes**
- CRUD ingredientes
- Flag alérgeno
- Control de stock

#### **Admin - Gestor de Pedidos**
- Tabla de pedidos con FSM
- Botones para avanzar estado
- Historial de cambios
- Búsqueda y filtros

#### **Admin - Vista Cocina**
- Pedidos EN_PREPARACION
- Botones: Marcar EN_CAMINO, ENTREGADO
- Orden de preparación visual

#### **Admin - Vista Cajero**
- Pedidos PENDIENTE/CONFIRMADO
- Confirmación de pago manual
- Crear pedidos rápidos

#### **Admin - Panel de Usuarios**
- Listar usuarios
- Asignar roles
- Gestión de permisos
- Soft delete

#### **MisDirecciones**
- Listar direcciones
- Crear/editar/eliminar
- Marcar dirección principal
- Formulario geolocalización

---

## 6. MODELO DE DATOS

### 6.1 Diagrama ER (Entidad-Relación)

```
┌─────────────────────┐
│      Usuario        │
├─────────────────────┤
│ id (PK)             │
│ email (UNIQUE)      │
│ password (hash)     │
│ nombre              │
│ apellido            │
│ celular             │
│ activo              │
│ creado_en           │
│ actualizado_en      │
│ eliminado_en        │
└──────────┬──────────┘
           │
      ┌────┴──────┐
      │ 1:N       │
      ▼           ▼
┌────────────┐ ┌──────────────┐
│UsuarioRol │ │  Pedido      │
├────────────┤ ├──────────────┤
│ usuario_id │ │ id (PK)      │
│ rol_codigo │ │ usuario_id   │
│ asignado_en│ │ direccion_id │
│ expires_at │ │ estado_cod.  │
└────────────┘ │ forma_pago   │
               │ tipo_entrega │
        ┌──────┤ subtotal     │
        │      │ descuento    │
        │      │ costo_envio  │
        │      │ total        │
        │      │ creado_en    │
        │      │ actualizado_ │
        │      └──────────────┘
        │           │
    ┌───┴─┐         │ 1:N
    │     │         ▼
    │   ┌─────────────────────┐
    │   │ DetallePedido       │
    │   ├─────────────────────┤
    │   │ detalle_id (PK)     │
    │   │ pedido_id (FK)      │
    │   │ producto_id (FK)    │
    │   │ cantidad            │
    │   │ precio_snapshot     │
    │   │ subtotal_snap       │
    │   │ personalizacion[]   │
    │   │ creado_en           │
    │   └─────────────────────┘
    │
┌───┴────────────────┐
│      Rol           │
├────────────────────┤
│ codigo (PK)        │
│ nombre             │
│ descripcion        │
└────────────────────┘
    │
    │ 1:N
    ▼
┌────────────────┐
│  RolPermiso    │
├────────────────┤
│ rol_codigo (FK)│
│ permiso_id(FK)│
└────────────────┘
    │
    └─────────┬──────────────┐
              │ 1:N          │
              ▼              ▼
    ┌──────────────────┐
    │   Permiso        │
    ├──────────────────┤
    │ id (PK)          │
    │ nombre (UNIQUE)  │
    │ descripcion      │
    └──────────────────┘

┌──────────────────────────┐
│      Categoria           │
├──────────────────────────┤
│ id (PK)                  │
│ nombre                   │
│ descripcion              │
│ activo                   │
│ creado_en                │
│ actualizado_en           │
│ eliminado_en             │
│ parent_id (FK) [opcional]│
│ imagen_url               │
└──────────┬───────────────┘
           │ 1:N
           ▼
    ┌──────────────────────┐
    │ProductoCategoria     │
    ├──────────────────────┤
    │ producto_id (FK)     │
    │ categoria_id (FK)    │
    │ (PK compuesta)       │
    └──────────────────────┘
           ▲
           │ 1:N
           │
    ┌──────────────────────┐
    │    Producto          │
    ├──────────────────────┤
    │ id (PK)              │
    │ nombre               │
    │ descripcion          │
    │ imagen_url           │
    │ stock_cantidad       │
    │ activo               │
    │ costo_produccion     │
    │ margen_ganancia      │
    │ precio               │
    │ creado_en            │
    │ actualizado_en       │
    │ eliminado_en         │
    └──────────┬───────────┘
               │ 1:N
               ▼
    ┌──────────────────────┐
    │ProductoIngrediente   │
    ├──────────────────────┤
    │ producto_id (FK)     │
    │ ingrediente_id (FK)  │
    │ cantidad_requerida   │
    │ es_removible         │
    │ (PK compuesta)       │
    └──────────────────────┘
            ▲
            │ 1:N
            │
    ┌──────────────────────┐
    │   Ingrediente        │
    ├──────────────────────┤
    │ id (PK)              │
    │ nombre               │
    │ disponible           │
    │ es_alergeno          │
    │ stock                │
    │ creado_en            │
    │ actualizado_en       │
    │ eliminado_en         │
    └──────────────────────┘

┌──────────────────────────┐
│  DireccionEntrega        │
├──────────────────────────┤
│ id (PK)                  │
│ usuario_id (FK)          │
│ alias                    │
│ calle                    │
│ numero                   │
│ piso                     │
│ depto                    │
│ ciudad                   │
│ provincia                │
│ codigo_postal            │
│ referencia               │
│ es_principal             │
│ creado_en                │
└──────────────────────────┘

┌──────────────────────────┐
│ HistorialEstadoPedido    │
├──────────────────────────┤
│ id (PK)                  │
│ pedido_id (FK)           │
│ estado_desde (nullable)  │
│ estado_hacia             │
│ usuario_id (FK)          │
│ motivo (nullable)        │
│ creado_en                │
│ (Append-only table)      │
└──────────────────────────┘

┌──────────────────────────┐
│        Pago              │
├──────────────────────────┤
│ id (PK)                  │
│ pedido_id (FK)           │
│ mp_payment_id            │
│ mp_status                │
│ mp_status_detail         │
│ transaction_amount       │
│ payment_method_id        │
│ external_reference       │
│ idempotency_key (UNIQUE) │
│ preference_id            │
│ init_point               │
│ creado_en                │
│ actualizado_en           │
└──────────────────────────┘

┌──────────────────────────┐
│       Imagen             │
├──────────────────────────┤
│ id (PK)                  │
│ public_id (Cloudinary)   │
│ url                      │
│ secure_url               │
│ formato                  │
│ ancho                    │
│ alto                     │
│ bytes                    │
│ folder                   │
│ recurso_tipo             │
│ subido_por_id (FK)       │
│ nombre_archivo           │
│ creado_en                │
│ eliminado_en             │
└──────────────────────────┘
```

### 6.2 Entidades Principales

#### **Usuario**
Identidad de usuario con autenticación y relación a roles

#### **Rol**
Define permisos y responsabilidades: ADMIN, CLIENTE, GESTOR_STOCK, GESTOR_PEDIDOS, CAJERO, COCINA

#### **Pedido**
Entidad central con FSM de 6 estados, captura de valores históricos y relación a detalles

#### **DetallePedido**
Detalles atomizados de cada pedido con snapshots de precios inmutables

#### **HistorialEstadoPedido**
Registro append-only de transiciones de estado con auditoría

#### **Producto**
Artículo del catálogo con stock, precios y margen de ganancia

#### **Categoria**
Clasificación jerárquica de productos con soporte para subcategorías

#### **Ingrediente**
Componentes de productos con flags de alergenicidad

#### **Pago**
Registro de transacciones MercadoPago con estados y referencias

#### **DireccionEntrega**
Direcciones de entrega asociadas a usuarios

#### **Imagen**
Registros de imágenes almacenadas en Cloudinary

---

## 7. API REST - ENDPOINTS

### 7.1 Prefix y Configuración

- **Base URL:** `/api/v1`
- **Documentación:** `/docs` (Swagger UI) y `/redoc` (ReDoc)
- **Error Format:** RFC 7807 (Problem Details)
- **Authentication:** Bearer token en header `Authorization`

### 7.2 Resumen de Endpoints

| Módulo | Método | Ruta | Rol | Descripción |
|--------|--------|------|-----|-------------|
| **AUTH** | POST | `/auth/register` | Público | Registro de usuario |
|  | POST | `/auth/login` | Público | Login (rate limited) |
|  | POST | `/auth/refresh` | Público | Refresco de token |
|  | POST | `/auth/logout` | Bearer | Logout |
|  | GET | `/auth/me` | Bearer | Perfil del usuario |
| **USUARIOS** | GET | `/usuarios` | ADMIN | Listar usuarios |
|  | GET | `/usuarios/{id}` | ADMIN | Detalle de usuario |
|  | PUT | `/usuarios/{id}` | ADMIN | Editar usuario |
|  | DELETE | `/usuarios/{id}` | ADMIN | Soft delete usuario |
| **CATEGORIAS** | GET | `/categorias` | Público | Listar categorías (árbol) |
|  | POST | `/categorias` | ADMIN | Crear categoría |
|  | PUT | `/categorias/{id}` | ADMIN | Editar categoría |
|  | DELETE | `/categorias/{id}` | ADMIN | Soft delete categoría |
| **PRODUCTOS** | GET | `/productos` | Público | Listar con filtros |
|  | GET | `/productos/{id}` | Público | Detalle con ingredientes |
|  | POST | `/productos` | ADMIN | Crear producto |
|  | PUT | `/productos/{id}` | ADMIN | Editar producto |
|  | PATCH | `/productos/{id}` | ADMIN | Toggle disponible |
|  | DELETE | `/productos/{id}` | ADMIN | Soft delete producto |
| **INGREDIENTES** | GET | `/ingredientes` | Público | Listar ingredientes |
|  | POST | `/ingredientes` | ADMIN | Crear ingrediente |
|  | PUT | `/ingredientes/{id}` | ADMIN | Editar ingrediente |
|  | DELETE | `/ingredientes/{id}` | ADMIN | Soft delete ingrediente |
| **PEDIDOS** | POST | `/pedidos` | CLIENT/CAJERO | Crear pedido (UoW) |
|  | GET | `/pedidos` | CLIENT/STAFF | Listar |
|  | GET | `/pedidos/{id}` | Propietario/STAFF | Detalle + historial |
|  | PATCH | `/pedidos/{id}/estado` | STAFF | Avanzar FSM |
|  | DELETE | `/pedidos/{id}` | CLIENT/STAFF | Cancelar |
|  | GET | `/pedidos/admin` | STAFF | Lista enriquecida |
| **PAGOS** | POST | `/pagos/crear` | CLIENT/CAJERO | Crear pago MP |
|  | POST | `/pagos/webhook` | Público | Webhook IPN MP |
|  | GET | `/pagos/{pedido_id}` | Propietario/ADMIN | Consulta pago |
| **IMAGENES** | POST | `/imagenes` | ADMIN | Upload Cloudinary |
|  | DELETE | `/imagenes/{public_id}` | ADMIN | Eliminar Cloudinary |
| **DIRECCIONES** | GET | `/direcciones` | CLIENT | Listar |
|  | POST | `/direcciones` | CLIENT | Crear |
|  | PUT | `/direcciones/{id}` | CLIENT | Editar |
|  | DELETE | `/direcciones/{id}` | CLIENT | Eliminar |
|  | PATCH | `/direcciones/{id}/principal` | CLIENT | Marcar principal |
| **ADMIN** | GET | `/admin/usuarios` | ADMIN | Listar usuarios |
|  | PUT | `/admin/usuarios/{id}/roles` | ADMIN | Asignar rol |
| **ESTADÍSTICAS** | GET | `/admin/estadisticas/resumen` | ADMIN | KPIs: ventas, ticket |
|  | GET | `/admin/estadisticas/ventas` | ADMIN | Ventas por período |
|  | GET | `/admin/estadisticas/productos-top` | ADMIN | Top 5 productos |
|  | GET | `/admin/estadisticas/pedidos-por-estado` | ADMIN | Dist. por estado |
|  | GET | `/admin/estadisticas/ingresos` | ADMIN | Ingresos por forma |
| **WEBSOCKET** | WS | `/ws/pedidos?token=<jwt>` | Bearer (JWT) | Feed de pedidos |

---

## 8. SISTEMA DE SEGURIDAD Y RBAC

### 8.1 Autenticación (JWT)

**Flujo:**
1. Usuario envía credenciales a `/auth/login`
2. Backend valida contraseña (bcrypt) y genera JWT
3. **Access Token:** 30 minutos (operaciones)
4. **Refresh Token:** 7 días (renovación segura)
5. Frontend almacena en localStorage (encrypted cookies en producción)
6. En cada request: `Authorization: Bearer <access_token>`

**Componentes:**
- `PyJWT` para generación/validación
- `bcrypt` para hashing de contraseñas
- Refresh token rotación
- Rate limiting 5/15 min en login/register

### 8.2 RBAC (Role-Based Access Control)

#### **6 Roles Implementados**

| Rol | Código | Responsabilidades |
|-----|--------|------------------|
| **Administrador** | ADMIN | Control total: CRUD todo, estadísticas, usuarios |
| **Cliente Tienda** | CLIENTE | Comprar, perfil, pedidos propios, direcciones |
| **Gestor de Stock** | GESTOR_STOCK | Productos, categorías, ingredientes, imágenes |
| **Gestor de Pedidos** | GESTOR_PEDIDOS | Avanzar todos los pedidos, ver todos |
| **Cajero** | CAJERO | Confirmar pagos, crear pedidos, ver pedidos |
| **Cocina** | COCINA | Ver pedidos, avanzar EN_PREPARACION→ENTREGADO |

#### **11 Permisos**

| Permiso | Descripción |
|---------|-------------|
| `VER_CATALOGO` | Ver productos, categorías, ingredientes |
| `GESTIONAR_PRODUCTOS` | CRUD productos |
| `GESTIONAR_CATEGORIAS` | CRUD categorías |
| `GESTIONAR_INGREDIENTES` | CRUD ingredientes |
| `CREAR_PEDIDO` | Realizar pedidos |
| `VER_PEDIDOS_PROPIOS` | Ver historial personal |
| `GESTIONAR_PEDIDOS` | Ver y gestionar todos |
| `VER_PERFIL_PROPIO` | Acceder a /me |
| `GESTIONAR_USUARIOS` | Admin usuarios |
| `GESTIONAR_DIRECCIONES` | CRUD direcciones |
| `GESTIONAR_IMAGENES` | Upload/delete imágenes |

#### **Matriz de Permisos**

| Permiso | ADMIN | CLIENTE | GESTOR_STOCK | GESTOR_PEDIDOS | CAJERO | COCINA |
|---------|-------|---------|--------------|----------------|--------|--------|
| VER_CATALOGO | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| GESTIONAR_PRODUCTOS | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| GESTIONAR_CATEGORIAS | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| GESTIONAR_INGREDIENTES | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| CREAR_PEDIDO | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ |
| VER_PEDIDOS_PROPIOS | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ |
| GESTIONAR_PEDIDOS | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ |
| VER_PERFIL_PROPIO | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| GESTIONAR_USUARIOS | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| GESTIONAR_DIRECCIONES | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| GESTIONAR_IMAGENES | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |

### 8.3 Protección CORS

```python
CORS_ORIGINS = [
    "http://localhost:5173",    # Dev frontend
    "http://localhost:3000",    # Alt frontend
    "https://yourdomain.com",   # Producción
]
```

### 8.4 Rate Limiting

- **Límite:** 5 intentos fallidos
- **Ventana:** 15 minutos
- **Endpoints:** `/auth/login` y `/auth/register`
- **Respuesta:** HTTP 429 + header `Retry-After`

### 8.5 HTTPS/TLS

- **En producción:** Requiere SSL/TLS
- **En desarrollo:** HTTP permitido
- **Cookies:** Secure flag en producción

---

## 9. INTEGRACIONES EXTERNAS

### 9.1 MercadoPago

#### **Configuración**

```
SDK: mercadopago==2.3.0
Modo: Checkout PRO
Tokenización: Tarjeta tokenizada por SDK React
```

#### **Flujo de Pago**

1. **Frontend:** Cliente completa datos en CardPayment
2. **SDK MP:** Tokeniza la tarjeta de forma segura
3. **Frontend → Backend:** Envía token + crear pago request
4. **Backend:** Genera pago con MercadoPago SDK
5. **MercadoPago:** Procesa pago y retorna status
6. **Backend → Webhook:** Recibe notificación IPN
7. **Backend:** Actualiza estado pedido basado en pago
8. **WebSocket:** Notifica al cliente en tiempo real

#### **Endpoints MercadoPago**

| Endpoint | Propósito |
|----------|----------|
| `POST /payments` | Crear pago con token |
| `GET /payments/{id}` | Consultar estado |
| `POST /v1/merchant_orders` | Crear orden (opcional) |

#### **Estados de Pago**

```
pending → approved → rejected / voided
```

#### **Formas de Pago Permitidas**

| Forma | Tipo Entrega | Implementación |
|-------|-------------|----------------|
| MercadoPago | Cualquiera | Obligatorio |
| Efectivo | EN_LOCAL | Pedido queda en PENDIENTE (cajero confirma) |
| Efectivo | DELIVERY | ❌ No permitido |

#### **Seguridad**

- ✅ Tokenización segura (nunca pasan datos de tarjeta por servidor)
- ✅ Idempotency keys UUID para evitar cobros duplicados
- ✅ Webhook firmado y validado
- ✅ Manejo seguro de credenciales en backend

### 9.2 Cloudinary

#### **Configuración**

```python
CLOUDINARY_CLOUD_NAME = "..."
CLOUDINARY_API_KEY = "..."
CLOUDINARY_API_SECRET = "..."
```

#### **Características**

- **Upload:** Backend-signed (SDK Python)
- **Folders:** foodstore/productos, foodstore/categorias
- **Formatos:** jpg, jpeg, png, webp
- **Límite:** 5MB por archivo
- **Transformaciones:** f_auto, q_auto, c_fill

#### **Endpoints**

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/v1/imagenes` | Upload a Cloudinary |
| DELETE | `/api/v1/imagenes/{public_id}` | Eliminar archivo |


### 9.3 PostgreSQL

#### **Características**

- **Versión:** 15+
- **Conexión:** SQLAlchemy pool
- **Tipo de BD:** Relacional
- **Migraciones:** Alembic

#### **Configuración de Conexión**

```
DATABASE_URL=postgresql://user:password@localhost:5432/foodstore
```

#### **Pool de Conexiones**

```python
pool_size=5
max_overflow=10
pool_pre_ping=True  # Validar conexiones
```

---

## 10. WEBSOCKETS - COMUNICACIÓN TIEMPO REAL

### 10.1 Arquitectura

#### **WSManager (Singleton)**

Gestiona pool de conexiones por canal:
- `/ws/pedidos` - Feed general
- Admin channel - Notificaciones administrativas

**Ubicación:** `app/core/ws_manager.py`

#### **Componentes**

```python
class WSManager:
    def __init__(self):
        self.connections: dict[str, list[WebSocket]] = {}
    
    async def connect(self, channel: str, websocket: WebSocket)
    async def disconnect(self, channel: str, websocket: WebSocket)
    async def broadcast(self, channel: str, message: dict)
```

### 10.2 Autenticación JWT en Handshake

```javascript
// Frontend
const token = authStore.getState().accessToken;
const ws = new WebSocket(`wss://api.example.com/ws/pedidos?token=${token}`);

// Backend
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    payload = verify_jwt(token)
    user_id = payload['sub']
    # Conexión autenticada
```

### 10.3 Estructura de Eventos

```json
{
  "type": "pedido.creado",
  "payload": {
    "pedido_id": 42,
    "usuario_id": 5,
    "estado_codigo": "PENDIENTE",
    "total": 400.00,
    "timestamp": "2026-06-14T14:30:00Z"
  }
}
```

```json
{
  "type": "pedido.estado.cambiado",
  "payload": {
    "pedido_id": 42,
    "estado_desde": "PENDIENTE",
    "estado_hacia": "CONFIRMADO",
    "usuario_actor_id": 1,
    "timestamp": "2026-06-14T14:35:00Z"
  }
}
```

### 10.4 Broadcast Post-Commit

```python
# Dentro de UoW (transacción)
pedido = service.crear_pedido(...)

# FUERA de UoW (post-commit)
await ws_manager.broadcast(
    channel="/ws/pedidos",
    message={
        "type": "pedido.creado",
        "payload": pedido.dict()
    }
)
```

### 10.5 Hooks Frontend

#### **usePedidoWebSocket**
```typescript
const { estado, historial, conexionActiva } = usePedidoWebSocket(pedido_id);
```

#### **useAdminOrdersFeed**
```typescript
const { pedidos, conexionActiva } = useAdminOrdersFeed();
```

### 10.6 Reconexión Exponencial

```javascript
const maxRetries = 5;
let retryCount = 0;
const baseDelay = 1000; // 1 segundo

async function connectWithRetry() {
    try {
        await connect();
        retryCount = 0; // Reset
    } catch (error) {
        if (retryCount < maxRetries) {
            const delay = baseDelay * Math.pow(2, retryCount);
            await new Promise(r => setTimeout(r, delay));
            retryCount++;
            await connectWithRetry();
        }
    }
}
```

---

## 11. TESTING Y QA

### 11.1 Estructura de Tests

```
foood-store-backend/tests/
├── conftest.py
├── test_auth.py
├── test_pedidos.py
├── test_estadisticas.py
├── test_pagos.py
├── test_uploads.py
└── test_websocket.py
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
| `producto_factory` | function | Factory Producto |
| `pedido_factory` | function | Factory Pedido |

### 11.3 Suite de Tests (20+)

#### **Auth Tests**
- ✅ Registro exitoso (201)
- ✅ Credenciales inválidas (401)
- ✅ Logout y revocación de refresh
- ✅ Rate limiting (429 después de 5 intentos)
- ✅ Refresh token válido

#### **Pedidos Tests**
- ✅ Crear pedido con stock disponible
- ✅ Crear pedido con stock insuficiente (400)
- ✅ Avanzar estado válido (FSM)
- ✅ Avanzar estado inválido (422)
- ✅ Cancelar pedido propio (solo PENDIENTE/CONFIRMADO)
- ✅ Historial append-only (no UPDATE ni DELETE)

#### **Estadísticas Tests**
- ✅ Resumen: ventas hoy, ticket promedio
- ✅ Ventas por período (DIARIO/MENSUAL)
- ✅ Top 5 productos por ingresos
- ✅ Distribución pedidos por estado
- ✅ Excluye pedidos CANCELADO

#### **Pagos Tests**
- ✅ Crear pago con token válido
- ✅ Webhook MercadoPago procesa correctamente
- ✅ Idempotency key evita duplicados

#### **Uploads Tests**
- ✅ Upload válido (jpg, png, webp)
- ✅ MIME inválido (400)
- ✅ Tamaño > 5MB (400)
- ✅ Eliminación exitosa

#### **WebSocket Tests**
- ✅ Conexión con JWT válido
- ✅ Conexión rechazada sin JWT
- ✅ Broadcast de eventos
- ✅ Reconexión después de desconexión

### 11.4 Ejecución de Tests

```bash
# Ejecutar todos los tests
pytest

# Con cobertura
pytest --cov=app --cov-report=html

# Tests específicos
pytest tests/test_auth.py -v

# Con markers
pytest -m "integration"
```

### 11.5 Cobertura de Código

- **Target:** 85%+
- **Herramienta:** pytest-cov
- **Exclusiones:** migraciones, configuración

---

## 12. GESTIÓN DE ARCHIVOS Y MEDIOS

### 12.1 Upload de Imágenes

#### **Flujo**

1. **Frontend:** Selecciona archivo (jpg, png, webp)
2. **Frontend:** Valida MIME type y tamaño (5MB)
3. **Frontend → Backend:** POST `/api/v1/imagenes`
4. **Backend:** Genera firma Cloudinary (backend-signed)
5. **Backend → Cloudinary:** Upload firmado
6. **Cloudinary:** Retorna public_id y URLs
7. **Backend → DB:** Registro en tabla Imagen
8. **Backend → Frontend:** Retorna metadatos

#### **Validaciones**

- MIME types: jpg, jpeg, png, webp
- Tamaño máximo: 5MB
- Carpeta: foodstore/productos o foodstore/categorias
- Overwrite: False (unique_filename: True)

---

## RESUMEN TÉCNICO

### Tecnologías Principales

- **Backend:** FastAPI + SQLModel + PostgreSQL
- **Frontend:** React + TypeScript + Tailwind CSS + Vite
- **Tiempo Real:** WebSockets con JWT
- **Pagos:** MercadoPago Checkout PRO
- **Medios:** Cloudinary
- **Testing:** pytest + TestClient

### Características Clave

✅ **RBAC completo** (6 roles, 11 permisos)  
✅ **FSM para pedidos** (6 estados validados)  
✅ **Unit of Work** (transacciones atómicas)  
✅ **WebSockets** (comunicación tiempo real)  
✅ **MercadoPago** (pagos online integrados)  
✅ **Cloudinary** (gestión de imágenes)  
✅ **Estadísticas** (KPIs y gráficos)  
✅ **20+ tests** (pytest con cobertura)  
✅ **API REST** (30+ endpoints documentados)  
✅ **Validaciones de stock en tiempo real** (pre-creación + pre-confirmación + alertas WebSocket)  
✅ **Soft delete** (auditoría completa)



