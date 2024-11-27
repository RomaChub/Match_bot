from pydantic import BaseModel


class SAboutAdd(BaseModel):
    tg_id: str
    dialog: str
    tread_id: str
