from abc import abstractmethod, ABC
from dataclasses import dataclass
from datetime import datetime, timezone
from dateutil.parser import isoparse
from enum import Enum
from pydantic import BaseModel, parse_obj_as, root_validator, validator
from typing import Dict, List, Literal, Optional, Union


############
# Base types
############
class StrictModel(BaseModel):
    class Config:
        extra = 'forbid'


class MsgType(Enum):
    CALL_INFO = 'callInfoUpdate'
    ROSTER = 'rosterUpdate'


@dataclass
class Anomaly:
    parameter: str
    value: Union[bool, float, str]


class Criterion(ABC):
    @abstractmethod
    def verify(self, message: dict, msg_type: MsgType) -> Optional[Anomaly]:
        pass


class Condition(ABC):
    @abstractmethod
    def satisfies(self, value: Union[bool, str, float]) -> bool:
        pass


##########
# Criteria
##########
class BooleanCriterion(StrictModel, Criterion):
    parameter: Literal['recording', 'streaming']
    conditions: bool

    def verify(self, message, msg_type):
        if msg_type != MsgType.CALL_INFO:
            return
        if (value := message[self.parameter]) != self.conditions:
            return Anomaly(self.parameter, value)


class ThresholdCondition(StrictModel, Condition):
    min: Optional[float]
    max: Optional[float]

    @root_validator
    def non_empty(cls, values):
        assert values.get('min') is not None or values.get('max') is not None, 'conditions cannot be empty'
        return values

    @validator('min', 'max')
    def non_negative(cls, v):
        if v is not None:
            assert v >= 0, 'condition value cannot be negative'
        return v

    @root_validator
    def monotonic(cls, values):
        mn, mx = values.get('min'), values.get('max')
        if mn is not None and mx is not None:
            assert mn <= mx, '"min" value must be <= "max" value'
        return values

    def satisfies(self, value):
        if self.min is not None and value < self.min:
            return False
        if self.max is not None and value > self.max:
            return False
        return True


class NumericCriterion(StrictModel, Criterion):
    parameter: Literal['time_diff', 'max_participants', 'active_speaker']
    conditions: Union[ThresholdCondition, float]

    @validator('conditions')
    def non_negative(cls, v):
        if isinstance(v, float):
            assert v >= 0, 'condition value cannot be negative'
        return v

    msg_params = {
        MsgType.CALL_INFO: {'time_diff', 'max_participants'},
        MsgType.ROSTER: {'active_speaker'}
    }

    def verify(self, message, msg_type):
        if self.parameter not in self.msg_params[msg_type]:
            return
        value = message[self.parameter]
        if isinstance(self.conditions, ThresholdCondition):
            if not self.conditions.satisfies(value):
                return Anomaly(self.parameter, value)
        elif value != self.conditions:
            return Anomaly(self.parameter, value)


def validate_time(time_str):
    if time_str is None:
        return
    if len(time_str) == 8:
        return datetime.strptime(time_str, '%H:%M:%S').replace(tzinfo=timezone.utc).time()
    elif len(time_str) == 5:
        return datetime.strptime(time_str, '%H:%M').replace(tzinfo=timezone.utc).time()
    else:
        raise ValueError('only "%H:%M:%S" and "%H:%M" time format allowed')


class DayCondition(StrictModel, Condition):
    day: int
    min_hour: Optional[str]
    max_hour: Optional[str]

    @validator('day')
    def in_range(cls, v):
        assert 1 <= v <= 7, 'days must be from 1 to 7, {} passed'.format(v)
        return v

    _min_hour_valid = validator('min_hour', allow_reuse=True)(validate_time)
    _max_hour_valid = validator('max_hour', allow_reuse=True)(validate_time)

    @root_validator
    def monotonic(cls, values):
        min_h, max_h = values.get('min_hour'), values.get('max_hour')
        if min_h is not None and max_h is not None:
            assert min_h <= max_h, '"min_hour" value must be <= "max_hour" value'
        return values

    def satisfies(self, date_time):
        if self.min_hour is not None and date_time < self.min_hour:
            return False
        if self.max_hour is not None and date_time > self.max_hour:
            return False
        return True


class DaysCriterion(StrictModel, Criterion):
    parameter: Literal['days']
    conditions: List[DayCondition]

    @validator('conditions')
    def non_empty(cls, v):
        assert len(v) > 0, '"days" conditions list cannot be empty'
        return v

    @validator('conditions')
    def unique(cls, v):
        assert len(v) == len({d.day for d in v}), '"days" cannot contain duplicate day values'
        return v

    def verify(self, message, _):
        week_day, date_time = message['week_day_number'], isoparse(message['datetime']).time()

        for c in self.conditions:
            if week_day == c.day:
                if not c.satisfies(date_time):
                    return Anomaly('datetime', str(date_time))
                break
        else:
            return Anomaly('day', week_day)


param_types = {
    'recording': BooleanCriterion,
    'streaming': BooleanCriterion,
    'time_diff': NumericCriterion,
    'max_participants': NumericCriterion,
    'active_speaker': NumericCriterion,
    'days': DaysCriterion
}


##################
# Module interface
##################
def validate(criteria: List[Dict]):
    validated = []
    for criterion in criteria:
        # note: using this instead of Union type because error messages SUCK otherwise
        if 'parameter' not in criterion:
            raise ValueError('each criterion must have valid "parameter" field')
        if criterion['parameter'] not in param_types:
            raise ValueError(f'unknown parameter {criterion["parameter"]}')
        param_type = param_types[criterion['parameter']]
        validated.append(parse_obj_as(param_type, criterion))
    return validated


def check(message: dict, msg_type: MsgType, criteria: List[Criterion]):
    anomalies = []
    for c in criteria:
        if (anomaly := c.verify(message, msg_type)) is not None:
            anomalies.append(anomaly)
    return anomalies


data_roster = {
    "datetime": "2020-06-08 06:11:24.794+0000",
    "call_id": "id121212",
    "initial": 0,
    "ringing": 1,
    "connected": 10,
    "onhold": 2,
    "active_speaker": 10,
    "presenter": 2,
    "endpoint_recording": 3,
    "hour": 10,
    "week_day_number": 3,
    "name": "name1"
}

data_call_info = {
    "adhoc": False,
    "call_id": "id12312e",
    "cospace": False,
    "current_participants": 10,
    "datetime": "2020-06-08 06:11:24.794+0000",
    "forwarding": True,
    "hour": 10,
    "locked": False,
    "lync_conferencing": True,
    "max_participants": 20,
    "mean_participants": 10.5,
    "recording": False,
    "streaming": True,
    "time_diff": 20000,
    "week_day_number": 4,
    "name": "name"}


admin_constraints = {
    "type": "threshold",
    "criteria": [
        {
            "parameter": "time_diff",
            "conditions": {
                "min": 0,
                "max": 42,
            }
        },
        {
            "parameter": "max_participants",
            "conditions": 2
        },
        {
            "parameter": "active_speaker",
            "conditions": 2
        },
        {
            "parameter": "recording",
            "conditions": True
        },
        {
            "parameter": "days",
            "conditions": [
                {
                    "day": 2,
                    "min_hour": "06:00",
                    "max_hour": "06:12",
                },
                {
                    "day": 3,
                    "min_hour": "07:00",
                    "max_hour": "20:30"
                }
            ]
        }
    ]
}

criteria = validate(admin_constraints['criteria'])
print(check(data_call_info, MsgType.CALL_INFO, criteria))
print(check(data_roster, MsgType.ROSTER, criteria))
