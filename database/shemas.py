from pydantic import BaseModel


class SAboutAdd(BaseModel):
    tg_id: int
    dialog: str
    tread_id: str
