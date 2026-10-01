from pydantic import BaseModel, Field


class AnswerRequest(BaseModel):
    question: str = Field(min_length=1)


class AnswerResponse(BaseModel):
    answer: str
    retrieved_sku: str
    retrieved_context: str


class AnswerWithContextRequest(BaseModel):
    question: str = Field(min_length=1)
    context: str = Field(min_length=1)


class AnswerWithContextResponse(BaseModel):
    answer: str
