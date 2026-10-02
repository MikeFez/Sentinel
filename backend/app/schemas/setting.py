from pydantic import BaseModel


class SettingResponse(BaseModel):
    key: str
    value: str

    class Config:
        from_attributes = True


class SettingUpdate(BaseModel):
    value: str
