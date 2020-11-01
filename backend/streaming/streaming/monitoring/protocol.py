"""Communication with worker processes over system pipes."""
# TODO:
#  - protobuf maybe? this kinda sucks
#  - subprocess doesn't have access to this module anyway, change PYTHONPATH or sth...
from typing import Literal, Union

from pydantic import BaseModel


class ThresholdCriteria(BaseModel):
    # TODO: will need a map from ParamName to numerical/textual/boolean condition
    dummy: dict


class ThresholdRequest(BaseModel):
    conf_id: str
    criteria: ThresholdCriteria

    def json(self, *args, **kwargs):
        return super().json(*args, **kwargs) + '\n'

    def bytes(self):
        return self.json().encode()


class MonitoringRequest(BaseModel):
    type: Literal['threshold', 'batch']
    criteria: Union[ThresholdCriteria]  # TODO: + BatchCriteria
