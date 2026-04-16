from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List

from core.database import get_session
from .models import Categoria
from .schemas import CategoriaCreate, CategoriaResponse

router = APIRouter(prefix="/categorias", tags=["Categorias"])

@router.post("/", response_model=CategoriaResponse)
def crear_categoria(categoria_in: CategoriaCreate, db: Session = Depends(get_session)):
    # Verificamos si ya existe una con ese nombre
    cat_existente = db.exec(select(Categoria).where(Categoria.nombre == categoria_in.nombre)).first()
    if cat_existente:
        raise HTTPException(status_code=400, detail="La categoría ya existe")
    
    # Creamos la nueva categoría
    nueva_categoria = Categoria(**categoria_in.model_dump())
    db.add(nueva_categoria)
    db.commit()
    db.refresh(nueva_categoria)
    return nueva_categoria

@router.get("/", response_model=List[CategoriaResponse])
def listar_categorias(db: Session = Depends(get_session)):
    # Solo traemos las que no están eliminadas (Soft Delete)
    categorias = db.exec(select(Categoria).where(Categoria.eliminado_en == None)).all()
    return categorias