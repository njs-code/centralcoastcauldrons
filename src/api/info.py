from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth

day = ""
hour = -1

router = APIRouter(
    prefix="/info",
    tags=["info"],
    dependencies=[Depends(auth.get_api_key)],
)

class Timestamp(BaseModel):
    day: str
    hour: int

@router.post("/current_time")
def post_time(timestamp: Timestamp):
    """
    Share current time.
    """
    global day 
    day = timestamp.day
    global hour 
    hour = timestamp.hour
    return "OK"

def current_day():
    global day
    return day

def current_hour():
    global hour
    return hour

