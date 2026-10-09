from pydantic import BaseModel
from datetime import datetime

class HealthResponse(BaseModel):
    status:str
    timestamp:datetime

class MessageResponse(BaseModel):
    message:str
    success:bool=True
    