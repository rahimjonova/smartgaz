from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


RegionStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=64)]
DistrictStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=100)]
MahallaStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=150)]
StreetStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=150)]
HouseStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]
FullNameStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=150)]


class MessageOut(BaseModel):
    detail: str
