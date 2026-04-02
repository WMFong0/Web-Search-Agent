from pydantic import BaseModel


class Product_Information(BaseModel):
    name: str
    description: str
    usage: str