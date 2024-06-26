from pydantic import BaseModel

class PostPrompt(BaseModel):
    prompt: str
    token: str
    engine: str
