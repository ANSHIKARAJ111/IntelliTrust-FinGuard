from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import UserLocation, User
from ..schemas import LocationIn
from ..auth import current_user

router=APIRouter(prefix="/api/location", tags=["location"])

@router.post("")
def save_location(body: LocationIn, db: Session=Depends(get_db), user: User=Depends(current_user)):
    loc=UserLocation(user_id=user.id,latitude=body.latitude,longitude=body.longitude,accuracy=body.accuracy)
    db.add(loc); db.commit()
    return {"saved":True}
