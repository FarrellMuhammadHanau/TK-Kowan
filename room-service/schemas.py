from pydantic import BaseModel

class RoomItem(BaseModel):
    name: str

class CreateRoomsRequest(BaseModel):
    rooms: list[RoomItem]

class CreateRoomsResponse(BaseModel):
    message: str

class GetRoomResponse(BaseModel):
    id: str
    name: str

class ValidateRoomItem(BaseModel):
    id: str

class ValidateExistenceRequest(BaseModel):
    rooms: list[ValidateRoomItem]

class ValidateResponse(BaseModel):
    valid: bool
    rooms: list[dict] = []