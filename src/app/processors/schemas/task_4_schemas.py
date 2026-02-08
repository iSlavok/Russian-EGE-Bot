from pydantic import BaseModel


class Task4Content(BaseModel):
    word: str
    incorrect_stress: int
