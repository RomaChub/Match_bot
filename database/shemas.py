from pydantic import BaseModel


class SAboutAdd(BaseModel):
    who: str
    what_can: str
    who_need: str
    user_id: str