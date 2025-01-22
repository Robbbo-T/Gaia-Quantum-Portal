import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .SensorDataIngestionService import app, get_db, Base, Sensor, SensorData

DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(scope="module")
def test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_register_sensor(test_db):
    response = client.post("/sensors", json={
        "sensor_id": "sensor_1",
        "tipo": "temperature",
        "descripcion": "Temperature sensor",
        "modelo": "T1000",
        "fabricante": "SensorCorp",
        "ubicacion": "Room 1"
    })
    assert response.status_code == 201
    assert response.json() == {"status": "success", "message": "Sensor registrado"}

def test_get_sensors(test_db):
    response = client.get("/sensors")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["sensor_id"] == "sensor_1"

def test_ingest_sensor_data(test_db):
    response = client.post("/sensors/sensor_1/data", json={
        "timestamp": "2023-01-01T00:00:00",
        "value": 25.5,
        "unit": "C",
        "location": "Room 1"
    })
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["message"] == "Data ingested"

def test_get_sensor_data(test_db):
    response = client.get("/sensors/sensor_1/data", params={
        "start_time": "2023-01-01T00:00:00",
        "end_time": "2023-01-01T23:59:59"
    })
    assert response.status_code == 200
    assert response.json()["sensor_id"] == "sensor_1"
    assert len(response.json()["data"]) == 1
    assert response.json()["data"][0]["value"] == 25.5

def test_database_connection(test_db):
    db = next(override_get_db())
    assert db is not None
    db.close()

def test_sensor_data_request_validation():
    from pydantic import ValidationError
    from .SensorDataIngestionService import SensorDataRequest

    with pytest.raises(ValidationError):
        SensorDataRequest(
            timestamp="invalid_timestamp",
            value="invalid_value",
            unit=123,
            location=456
        )

def test_sensor_request_validation():
    from pydantic import ValidationError
    from .SensorDataIngestionService import SensorRequest

    with pytest.raises(ValidationError):
        SensorRequest(
            sensor_id=123,
            tipo=456,
            descripcion=789,
            modelo=101112,
            fabricante=131415,
            ubicacion=161718
        )

def test_get_db_dependency():
    db = next(override_get_db())
    assert db is not None
    db.close()

def test_error_handling_invalid_input(test_db):
    response = client.post("/sensors", json={
        "sensor_id": 123,
        "tipo": 456,
        "descripcion": 789,
        "modelo": 101112,
        "fabricante": 131415,
        "ubicacion": 161718
    })
    assert response.status_code == 422

def test_error_handling_database_error(test_db, monkeypatch):
    def mock_commit():
        raise Exception("Database error")

    monkeypatch.setattr(TestingSessionLocal, "commit", mock_commit)

    response = client.post("/sensors", json={
        "sensor_id": "sensor_2",
        "tipo": "humidity",
        "descripcion": "Humidity sensor",
        "modelo": "H2000",
        "fabricante": "SensorCorp",
        "ubicacion": "Room 2"
    })
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal Server Error"}
