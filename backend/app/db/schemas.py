from pydantic import BaseModel
from datetime import datetime

class DomainBase(BaseModel):
    domain_name: str

class DomainCreate(DomainBase):
    pass

class Domain(DomainBase):
    updated_on: datetime

    class Config:
        orm_mode = True
