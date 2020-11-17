import json
from marshmallow import Schema, fields, ValidationError

from .validation import validate


class JSONString(fields.Field):
    # valid string to output dict
    def _deserialize(self, value, attr, obj, **kwargs):
        return json.dumps(value)

    # input dict to valid string
    def _serialize(self, value, attr, obj, **kwargs):
        return json.loads(value)


def validate_criteria(data):
    try:
        validate(json.loads(data))
    except ValueError as e:
        raise ValidationError(str(e))


class MeetingSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str()
    criteria = JSONString(validate=validate_criteria)  # TODO: no better idea for now for a JSON field


meeting_schema = MeetingSchema()
