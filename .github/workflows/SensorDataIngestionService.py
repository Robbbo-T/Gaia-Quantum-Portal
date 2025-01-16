from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
import datetime

# Configuración de la base de datos
DATABASE_URL = "postgresql://user:password@host:port/database" # Reemplaza con tu configuración
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Definición del modelo de datos
class Sensor(Base):
    __tablename__ = "sensors"
    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(String, unique=True, index=True)
    tipo = Column(String)
    descripcion = Column(String)
    modelo = Column(String)
    fabricante = Column(String)
    ubicacion = Column(String)

class SensorData(Base):
    __tablename__ = "sensor_data"
    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(String, index=True)
    timestamp = Column(DateTime)
    value = Column(Float)
    unit = Column(String)
    location = Column(String)

Base.metadata.create_all(bind=engine)

# Esquemas Pydantic para las solicitudes
class SensorDataRequest(BaseModel):
    timestamp: datetime.datetime
    value: float
    unit: str
    location: str

class SensorRequest(BaseModel):
    sensor_id: str
    tipo: str
    descripcion: str
    modelo: str
    fabricante: str
    ubicacion: str

# Dependencia para obtener una sesión de la base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Inicialización de la aplicación FastAPI
app = FastAPI()

# Endpoint para registrar un nuevo sensor
@app.post("/sensors", status_code=201)
def register_sensor(sensor: SensorRequest, db: Session = Depends(get_db)):
    db_sensor = Sensor(**sensor.dict())
    db.add(db_sensor)
    db.commit()
    db.refresh(db_sensor)
    return {"status": "success", "message": "Sensor registrado"}

# Endpoint para obtener la lista de sensores
@app.get("/sensors")
def get_sensors(db: Session = Depends(get_db)):
    sensors = db.query(Sensor).all()
    return sensors

# Endpoint para ingerir datos del sensor
@app.post("/sensors/{sensor_id}/data")
def ingest_sensor_data(sensor_id: str, data: SensorDataRequest, db: Session = Depends(get_db)):
    db_data = SensorData(sensor_id=sensor_id, **data.dict())
    db.add(db_data)
    db.commit()
    db.refresh(db_data)
    return {"status": "success", "message": "Data ingested", "data_id": db_data.id}

# Endpoint para obtener datos históricos del sensor
@app.get("/sensors/{sensor_id}/data")
def get_sensor_data(sensor_id: str, start_time: datetime.datetime, end_time: datetime.datetime, db: Session = Depends(get_db)):
    data = db.query(SensorData).filter(
        SensorData.sensor_id == sensor_id,
        SensorData.timestamp >= start_time,
        SensorData.timestamp <= end_time
    ).all()
    return {"sensor_id": sensor_id, "data": data}


