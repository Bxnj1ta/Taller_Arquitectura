from pydantic import BaseModel, constr

class ItemCreate(BaseModel):
    name: constr(min_length=1, max_length=100)
    description: constr(max_length=250) = None
