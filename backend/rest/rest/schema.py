import json
from marshmallow import fields, Schema, ValidationError
from marshmallow.validate import Range

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
    name = fields.Str(required=True)
    criteria = JSONString(required=True, validate=validate_criteria)  # TODO: no better idea for now for a JSON field


class AnomalySchema(Schema):
    id = fields.Int(dump_only=True)
    meeting_name = fields.Str(required=True)
    datetime = fields.DateTime(required=True)
    reason = JSONString(required=True)


class AnomalyRequestSchema(Schema):
    name = fields.Str(required=True)
    count = fields.Int(required=True, validate=Range(min=1, error='count must be positive'))


anomaly_schema = AnomalySchema()
meeting_schema = MeetingSchema()

anomaly_request_schema = AnomalyRequestSchema()
