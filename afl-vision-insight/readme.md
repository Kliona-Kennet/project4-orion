 cd backend
 venv\Scripts\activate 
uvicorn main:app --reload --port 8000

cd crowd_monitoring_service
uvicorn app.main:app --reload --port 8002

cd player_tracking_service
uvicorn app.main:app --reload --port 8001