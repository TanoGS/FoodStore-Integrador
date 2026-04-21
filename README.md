
### 2. Configurar y levantar el Backend (FastAPI)

1. Abre una terminal y dirígete a la carpeta del backend:
   \`\`\`bash
   cd foood-store-backend
   \`\`\`
2. Crea y activa un entorno virtual:
   \`\`\`bash
   python -m venv .venv
   # En Windows (PowerShell):
   .\.venv\Scripts\Activate.ps1
   \`\`\`
3. Instala las dependencias:
   \`\`\`bash
   pip install -r requirements.txt
   \`\`\`
4. Configura las variables de entorno:
   Crea un archivo \`.env\` en la carpeta del backend copiando la estructura de tu base de datos local:
   \`\`\`env
   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/foodstore_db
   CORS_ORIGINS=["http://localhost:5173"]
   \`\`\`
5. Ejecuta las migraciones para crear las tablas en PostgreSQL:
   \`\`\`bash
   alembic upgrade head
   \`\`\`
6. (Opcional) Inicializa los datos base (Roles y Administrador de prueba):
   \`\`\`bash
   python seed.py
   \`\`\`
7. Inicia el servidor de desarrollo:
   \`\`\`bash
   uvicorn main:app --reload
   \`\`\`
   *La API estará disponible en `http://localhost:8000/docs`*

### 3. Configurar y levantar el Frontend (React)

1. Abre una nueva terminal y dirígete a la carpeta del frontend:
   \`\`\`bash
   cd food-store-frontend
   \`\`\`
2. Instala las dependencias de Node:
   \`\`\`bash
   npm install
   \`\`\`
3. Configura las variables de entorno:
   Crea un archivo \`.env\` en la carpeta del frontend:
   \`\`\`env
   VITE_API_BASE_URL=http://localhost:8000/api/v1
   \`\`\`
4. Inicia el entorno de desarrollo de Vite:
   \`\`\`bash
   npm run dev
   \`\`\`
   *La aplicación estará disponible en `http://localhost:5173`*

---

## Credenciales de Prueba

Si ejecutaste el script \`seed.py\`, puedes ingresar al panel de administración temporal utilizando:
* **Email:** admin@foodstore.com
* **Password:** 123

## Agregar las importaciones, Eje: 
alembic/env.py
from app.modules.categoria.models import Categoria

## Corre la migración: 
alembic revision --autogenerate -m "Tabla categorias" 
alembic upgrade head
