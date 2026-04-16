from sqlmodel import Session, select
from core.database import engine
from app.modules.usuarios.models import Rol, Usuario

def inicializar_datos():
    with Session(engine) as db:
        # 1. Buscar o crear el rol ADMIN
        rol_admin = db.exec(select(Rol).where(Rol.nombre == "ADMIN")).first()
        if not rol_admin:
            rol_admin = Rol(nombre="ADMIN", descripcion="Administrador total del sistema")
            db.add(rol_admin)
            db.commit()
            db.refresh(rol_admin)
            print("✅ Rol ADMIN creado.")

        # 2. Buscar o crear el rol CLIENTE (por las dudas)
        rol_cliente = db.exec(select(Rol).where(Rol.nombre == "CLIENTE")).first()
        if not rol_cliente:
            rol_cliente = Rol(nombre="CLIENTE", descripcion="Usuario regular")
            db.add(rol_cliente)
            db.commit()
            print("✅ Rol CLIENTE creado.")

        # 3. Crear el usuario Administrador
        email_admin = "admin@foodstore.com"
        usuario_admin = db.exec(select(Usuario).where(Usuario.email == email_admin)).first()
        
        if not usuario_admin:
            nuevo_admin = Usuario(
                nombre="Super",
                apellido="Admin",
                email=email_admin,
                password_hash="123", # Contraseña en texto plano temporalmente
                telefono="0000000000",
                rol_id=rol_admin.id
            )
            db.add(nuevo_admin)
            db.commit()
            print(f"✅ Usuario Admin creado exitosamente!")
            print(f"   -> Email: {email_admin}")
            print(f"   -> Password: 123")
        else:
            print("⚠️ El usuario Admin ya existía en la base de datos.")

if __name__ == "__main__":
    print("Iniciando la carga de datos (Seed)...")
    inicializar_datos()
    print("¡Proceso finalizado!")