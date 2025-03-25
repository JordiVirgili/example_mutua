import os
from datetime import datetime, timedelta, date
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from models import (User, Paciente, Tratamiento, Autorizacion, Factura, DetalleFactura, ServicioUtilizado,
                    ServicioClinica, TokenBase, TokenData, UserInDB, PacienteInDB, TratamientoInDB, AutorizacionInDB,
                    AutorizacionWithDetails, FacturaInDB, DetalleFacturaInDB, ServicioUtilizadoInDB,
                    ServicioClinicaInDB, InformeServicios)
from database import (get_db, verify_password, get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES,
                      SECRET_KEY, ALGORITHM, init_db)

# Inicialización de FastAPI
app = FastAPI(title="API de Servicios de Mutua para Clínica Hospitalaria",
    description="API para gestionar servicios entre una mutua y una clínica hospitalaria", version="1.0.0")

# Configuración de CORS
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"],
    allow_headers=["*"], )

# Configuración de OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# Dependencia para obtener el usuario actual
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas",
        headers={"WWW-Authenticate": "Bearer"}, )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.username == token_data.username).first()
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Usuario inactivo")
    return current_user


# Inicializar la base de datos al iniciar la aplicación
@app.on_event("startup")
def startup_db_client():
    db = next(get_db())
    init_db(db)


# Rutas de autenticación
@app.post("/token", response_model=TokenBase)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"}, )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/users/me", response_model=UserInDB)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user


# Rutas para servicios de la mutua
@app.post("/autorizaciones/", tags=["Autorizaciones"])
async def autorizar_tratamiento(id_paciente: int, id_tratamiento: int, comentarios: Optional[str] = None,
        current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """
    Autorizar un tratamiento o servicio solicitado para un paciente.
    """
    # Verificar si el paciente existe
    paciente = db.query(Paciente).filter(Paciente.id == id_paciente).first()
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    # Verificar si el tratamiento existe
    tratamiento = db.query(Tratamiento).filter(Tratamiento.id == id_tratamiento).first()
    if not tratamiento:
        raise HTTPException(status_code=404, detail="Tratamiento no encontrado")

    # Verificar si el tratamiento requiere autorización
    if not tratamiento.requiere_autorizacion:
        return {"mensaje": "Este tratamiento no requiere autorización previa"}

    # Crear nueva autorización
    nueva_autorizacion = Autorizacion(id_paciente=id_paciente, id_tratamiento=id_tratamiento,
        fecha_solicitud=date.today(), estado="aprobada",  # Por defecto se aprueba, en un caso real habría validación
        comentarios=comentarios)

    db.add(nueva_autorizacion)
    db.commit()
    db.refresh(nueva_autorizacion)

    return {"mensaje": "Tratamiento autorizado correctamente", "autorizacion": nueva_autorizacion}


@app.get("/autorizaciones/paciente/{id_paciente}", response_model=List[AutorizacionInDB], tags=["Autorizaciones"])
async def consultar_historial_autorizaciones(id_paciente: int, current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)):
    """
    Consultar el historial de autorizaciones previas de un paciente.
    """
    # Verificar si el paciente existe
    paciente = db.query(Paciente).filter(Paciente.id == id_paciente).first()
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    # Buscar autorizaciones del paciente
    autorizaciones = db.query(Autorizacion).filter(Autorizacion.id_paciente == id_paciente).all()

    return autorizaciones


@app.get("/facturas/paciente/{id_paciente}", response_model=List[FacturaInDB], tags=["Facturas"])
async def consultar_estado_facturas(id_paciente: int, current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)):
    """
    Consultar el estado de las facturas asociadas a un paciente.
    """
    # Verificar si el paciente existe
    paciente = db.query(Paciente).filter(Paciente.id == id_paciente).first()
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    # Buscar facturas del paciente
    facturas = db.query(Factura).filter(Factura.id_paciente == id_paciente).all()

    return facturas


@app.get("/servicios/informe/{id_paciente}", response_model=InformeServicios, tags=["Servicios"])
async def solicitar_informe_servicios(id_paciente: int, fecha_inicio: Optional[date] = None,
        fecha_fin: Optional[date] = None, current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)):
    """
    Solicitar un informe de servicios utilizados por un paciente en un período determinado.
    """
    # Verificar si el paciente existe
    paciente = db.query(Paciente).filter(Paciente.id == id_paciente).first()
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    # Buscar servicios del paciente con filtro de fechas opcional
    query = db.query(ServicioUtilizado).filter(ServicioUtilizado.id_paciente == id_paciente)

    if fecha_inicio:
        query = query.filter(ServicioUtilizado.fecha >= fecha_inicio)

    if fecha_fin:
        query = query.filter(ServicioUtilizado.fecha <= fecha_fin)

    servicios = query.all()

    # Calcular total
    total_costo = sum(s.costo for s in servicios)

    return {"paciente": f"{paciente.nombre} {paciente.apellido}", "numero_afiliado": paciente.numero_afiliado,
        "periodo": {"desde": fecha_inicio.isoformat() if fecha_inicio else "Inicio",
            "hasta": fecha_fin.isoformat() if fecha_fin else "Actualidad"}, "servicios": servicios,
        "total": total_costo}


# Rutas adicionales para información de referencia
@app.get("/pacientes/", response_model=List[PacienteInDB], tags=["Referencia"])
async def listar_pacientes(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """
    Listar todos los pacientes registrados (para referencia).
    """
    return db.query(Paciente).all()


@app.get("/tratamientos/", response_model=List[TratamientoInDB], tags=["Referencia"])
async def listar_tratamientos(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """
    Listar todos los tratamientos disponibles (para referencia).
    """
    return db.query(Tratamiento).all()


# Rutas para el catálogo de servicios de la clínica
@app.get("/servicios-clinica/", response_model=List[ServicioClinicaInDB], tags=["Servicios Clínica"])
async def listar_servicios_clinica(current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)):
    """
    Listar todos los servicios del catálogo de la clínica.
    """
    return db.query(ServicioClinica).all()


@app.get("/servicios-clinica/mutua", response_model=List[ServicioClinicaInDB], tags=["Servicios Clínica"])
async def listar_servicios_incluidos_mutua(current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)):
    """
    Listar los servicios del catálogo incluidos en la mutua.
    """
    return db.query(ServicioClinica).filter(ServicioClinica.incluido_mutua == True).all()


# Ruta para verificar si un paciente pertenece a la mutua
@app.get("/pacientes/verificar/{afiliado}", tags=["Pacientes"])
async def verificar_pertenencia_mutua(afiliado: str, current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)):
    """
    Verificar si un paciente pertenece a la mutua.
    """
    paciente = db.query(Paciente).filter(Paciente.numero_afiliado == afiliado).first()
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    return {"id": paciente.id, "nombre": paciente.nombre, "apellido": paciente.apellido,
        "numero_afiliado": paciente.numero_afiliado, "pertenece_mutua": paciente.pertenece_mutua}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)