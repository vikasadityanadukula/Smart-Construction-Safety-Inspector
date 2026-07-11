from pydantic import BaseModel

class ViolationCreate(BaseModel):
    worker_id: int
    helmet: bool
    vest: bool
    zone: str
    time: str