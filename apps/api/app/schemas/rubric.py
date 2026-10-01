import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RubricDimension(BaseModel):
    key: str
    description: str


class RubricCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    dimensions: list[RubricDimension] = Field(min_length=1)


class RubricRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    dimensions: list[dict]
    created_at: datetime
