from pydantic import BaseModel, EmailStr
from typing import Optional, List


class UserCreate(BaseModel):
    first_name: str
    last_name: Optional[str]
    email: EmailStr
    phone_number: str
    password: str
    terms_and_conditions: bool
    street_address: str
    city: str
    state: str
    zip_code: str
    country: str

class UserInDB(UserCreate):
    id: str

class Prompt(BaseModel):
    id: str
    prompts: List[str]

class Output(BaseModel):
    id: str
    outputs: List[str]