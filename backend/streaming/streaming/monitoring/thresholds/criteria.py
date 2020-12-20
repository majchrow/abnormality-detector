from abc import abstractmethod, ABC
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
    CALLS = 'callListUpdate'
    CALL_INFO = 'callInfoUpdate'
    ROSTER = 'rosterUpdate'


class Anomaly(BaseModel):
    parameter: str
    value: Union[float, bool, str]
    condition_type: str
    condition_value: Union[float, bool, str, List]


class Criterion(ABC):
    @abstractmethod
    def verify(self, message: dict, msg_type: MsgType) -> Optional[Anomaly]:
        pass


class Condition(ABC):
    @abstractmethod
    def min_satisfies(self, value: Union[bool, str, float]) -> bool:
        pass

    @abstractmethod
    def max_satisfies(self, value: Union[bool, str, float]) -> bool:
        pass


##########
# Criteria
##########
class BooleanCriterion(StrictModel, Criterion):
    parameter: Literal['recording', 'streaming']
    conditions: bool

    @validator('conditions', pre=True)
    def is_bool(cls, v):
        assert isinstance(v, bool), f'value {v} is not a bool'
        return v

    def verify(self, message, msg_type):
        if msg_type != MsgType.CALL_INFO:
            return
        if (value := message[self.parameter]) != self.conditions:
            return Anomaly(
                parameter=self.parameter, value=value, condition_type='eq', condition_value=self.conditions
            )


class ThresholdCondition(StrictModel, Condition):
    min: Optional[int]
    max: Optional[int]

    @validator('min', 'max', pre=True)
    def is_int(cls, v):
        if v is not None:
            assert not isinstance(v, bool), f'value {v} is not an integer'
            assert isinstance(v, int), f'value {v} is not integer'
        return v

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

    def min_satisfies(self, value):
        if self.min is not None and value < self.min:
            return False
        return True

    def max_satisfies(self, value):
        if self.max is not None and value > self.max:
            return False
        return True


nc_msg_params = {
    MsgType.CALLS: {},
    MsgType.CALL_INFO: {'max_participants'},
    MsgType.ROSTER: {'active_speaker'}
}


class NumericCriterion(StrictModel, Criterion):
    parameter: Literal['max_participants', 'active_speaker']
    conditions: Union[ThresholdCondition, int]

    @validator('conditions', pre=True)
    def is_int(cls, v):
        if not isinstance(v, dict):
            assert not isinstance(v, bool), f'value {v} is not an integer'
            assert isinstance(v, int), f'value {v} is not an integer'
        return v

    @validator('conditions')
    def non_negative(cls, v):
        if isinstance(v, int):
            assert v >= 0, 'condition value cannot be negative'
        return v

    def verify(self, message, msg_type):
        if self.parameter not in nc_msg_params[msg_type]:
            return
        value = message[self.parameter]
        if isinstance(self.conditions, ThresholdCondition):
            if not self.conditions.max_satisfies(value):
                return Anomaly(
                    parameter=self.parameter,
                    value=value,
                    condition_type='max',
                    condition_value=self.conditions.max
                )
            if not self.conditions.min_satisfies(value):
                return Anomaly(
                    parameter=self.parameter,
                    value=value,
                    condition_type='min',
                    condition_value=self.conditions.min
                )
        elif value != self.conditions:
            return Anomaly(
                parameter=self.parameter, value=value, condition_type='eq', condition_value=self.conditions
            )


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

    @validator('day', pre=True)
    def is_int(cls, v):
        assert not isinstance(v, bool), f'value {v} is not an integer'
        assert isinstance(v, int), f'value {v} is not an integer'
        return v

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

    def min_satisfies(self, date_time):
        if self.min_hour is not None and date_time < self.min_hour:
            return False
        return True

    def max_satisfies(self, date_time):
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

    def verify(self, message, msg_type):
        if msg_type == MsgType.CALLS:
            return
        
        if isinstance(message['datetime'], datetime):
            week_day, date_time = message['week_day_number'], message['datetime']
        else:
            week_day, date_time = message['week_day_number'], isoparse(message['datetime']).time()

        for c in self.conditions:
            if week_day == c.day:
                if not c.min_satisfies(date_time):
                    return Anomaly(
                        parameter='datetime',
                        value=str(date_time),
                        condition_type='min',
                        condition_value=c.min_hour
                    )
                if not c.max_satisfies(date_time):
                    return Anomaly(
                        parameter='datetime',
                        value=str(date_time),
                        condition_type='max',
                        condition_value=c.max_hour
                    )
                break
        else:
            return Anomaly(
                parameter='day',
                value=float(week_day),
                condition_type='in',
                condition_value=[c.day for c in self.conditions]
            )


class TimeCriterion(NumericCriterion):
    parameter: Literal['time_diff']

    @validator('conditions')
    def is_dict(cls, v):
        assert isinstance(v, ThresholdCondition), f'value {v} must be a dictionary'
        return v

    def verify(self, message, msg_type):
        if msg_type == MsgType.CALLS:
            value = message['duration']
            if message['finished'] and not self.conditions.min_satisfies(value):
                return Anomaly(
                    parameter=self.parameter,
                    value=value,
                    condition_type='min',
                    condition_value=self.conditions.min
                )
            elif not self.conditions.max_satisfies(value):
                return Anomaly(
                    parameter=self.parameter,
                    value=value,
                    condition_type='max',
                    condition_value=self.conditions.max
                )
        elif msg_type == MsgType.CALL_INFO:
            value = message['time_diff']
            if not self.conditions.max_satisfies(value):
                return Anomaly(
                    parameter=self.parameter,
                    value=value,
                    condition_type='max',
                    condition_value=self.conditions.max
                )


param_types = {
    'recording': BooleanCriterion,
    'streaming': BooleanCriterion,
    'time_diff': TimeCriterion,
    'max_participants': NumericCriterion,
    'active_speaker': NumericCriterion,
    'days': DaysCriterion
}


##################
# Module interface
##################
def validate(criteria: List[Dict]) -> List[Criterion]:
    if not criteria:
        raise ValueError('empty criteria passed')
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


def check(message: dict, msg_type: MsgType, criteria: List[Criterion]) -> List[Anomaly]:
    anomalies = []
    for c in criteria:
        if (anomaly := c.verify(message, msg_type)) is not None:
            anomalies.append(anomaly)
    return anomalies
