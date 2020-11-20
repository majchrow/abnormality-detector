import json
from marshmallow import Schema, fields, ValidationError

from .validation import validate


class JSONString(fields.Field):
    # a dict to JSON string (really - dict is the serialized form)
    def _deserialize(self, value, attr, obj, **kwargs):
        return json.dumps(value)

    # a JSON string to dict
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


class AnomalySchema(Schema):
    id = fields.Int(dump_only=True)
    meeting_name = fields.Str()
    call_id = fields.Str()
    datetime = fields.DateTime()
    reason = fields.Str()


anomaly_schema = AnomalySchema()
meeting_schema = MeetingSchema()
