from fastapi import FastAPI, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from . import models, schemas, services, database
from .tasks import mock_background_task

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Docker Benchmark API")

@app.post("/users/", response_model=schemas.UserResponse)
def create_user(user: schemas.UserCreate, background_tasks: BackgroundTasks, db: Session = Depends(database.get_db)):
    db_user = models.User(name=user.name, email=user.email)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    background_tasks.add_task(mock_background_task, user.email)
    return db_user

@app.get("/analytics/")
def get_analytics():
    results = services.run_heavy_analytics()
    return {"status": "success", "data": results}

# INITIAL_COMMENT_MARKER
