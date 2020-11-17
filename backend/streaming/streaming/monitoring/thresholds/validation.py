from datetime import datetime
from pydantic import BaseModel, parse_obj_as, root_validator, validator
from typing import Dict, List, Literal, Optional, Union


class Model(BaseModel):
    class Config:
        extra = 'forbid'


class BooleanCriterion(Model):
    parameter: Literal['recording', 'streaming']
    conditions: bool


class ThresholdCondition(Model):
    min: Optional[int]
    max: Optional[int]

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


class NumericCriterion(Model):
    parameter: Literal['time_diff', 'max_participants', 'active_speaker']
    conditions: Union[ThresholdCondition, int]

    @validator('conditions')
    def non_negative(cls, v):
        if isinstance(v, int):
            assert v >= 0, 'condition value cannot be negative'
        return v


def validate_time(time_str):
    if len(time_str) == 8:
        return datetime.strptime(time_str, '%H:%M:%S')
    elif len(time_str) == 5:
        return datetime.strptime(time_str, '%H:%M')
    else:
        raise ValueError('only "%H:%M:%S" and "%H:%M" time format allowed')


class DayCriterion(Model):
    day: int
    min_hour: Optional[str]
    max_hour: Optional[str]

    @validator('day')
    def in_range(cls, v):
        assert 1 <= v <= 7, 'days must be from 1 to 7, {} passed'.format(v)
        return v

    # TODO: to decide
    # @root_validator
    # def non_empty(cls, values):
    #     min_h, max_h = values.get('min_hour'), values.get('max_hour')
    #     assert min_h is not None or max_h is not None, '"day" condition cannot be empty'
    #     return values

    _min_hour_valid = validator('min_hour', allow_reuse=True)(validate_time)
    _max_hour_valid = validator('max_hour', allow_reuse=True)(validate_time)

    @root_validator
    def monotonic(cls, values):
        min_h, max_h = values.get('min_hour'), values.get('max_hour')
        if min_h is not None and max_h is not None:
            assert min_h <= max_h, '"min_hour" value must be <= "max_hour" value'
        return values


class DaysCriterion(Model):
    parameter: Literal['days']
    conditions: List[DayCriterion]

    @validator('conditions')
    def non_empty(cls, v):
        assert len(v) > 0, '"days" conditions list cannot be empty'
        return v

    @validator('conditions')
    def unique(cls, v):
        assert len(v) == len({d.day for d in v}), '"days" cannot contain duplicate day values'
        return v


param_types = {
    'recording': BooleanCriterion,
    'streaming': BooleanCriterion,
    'time_diff': NumericCriterion,
    'max_participants': NumericCriterion,
    'active_speaker': NumericCriterion,
    'days': DaysCriterion
}


def validate(criteria: List[Dict]):
    validated = []
    for criterion in criteria:
        # note: using this instead of Union type because error messages SUCK otherwise
        if 'parameter' not in criterion:
            raise ValueError('single criterion must have valid "parameter" field')
        if criterion['parameter'] not in param_types:
            raise ValueError(f'unknown parameter {criterion["parameter"]}')
        param_type = param_types[criterion['parameter']]
        validated.append(parse_obj_as(param_type, criterion))
    return validated


###
test_criteria = [
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
        "parameter": "days",
        "conditions": [
            {
                "day": 1,
                "min_hour": "06:00",
                "max_hour": "06:11",
            },
            {
                "day": 2,
                "min_hour": "05:00:00",
                "max_hour": "20:30"
            }
        ]
    }
]

pydantic_validate(test_criteria)
