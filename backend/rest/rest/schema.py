import json
from marshmallow import fields, Schema, ValidationError
from marshmallow.validate import Range

from .criteria import validate


class JSONString(fields.Field):
    # a dict to JSON string (really - dict is the serialized form)
    def _deserialize(self, value, attr, obj, **kwargs):
        return json.dumps(value)

    # a JSON string to dict
    def _serialize(self, value, attr, obj, **kwargs):
        if value is not None:
            return json.loads(value)
        else:
            return []


def validate_criteria(data):
    try:
        validate(json.loads(data))
    except ValueError as e:
        raise ValidationError(str(e))


class MeetingSchema(Schema):
    id = fields.Int(dump_only=True)
    meeting_name = fields.Str(required=True, data_key="name")
    meeting_number = fields.Str(required=True, dump_only=True)
    criteria = JSONString(required=True, validate=validate_criteria)


class MeetingRequestSchema(Schema):
    name = fields.Str(required=True)
    criteria = JSONString(required=True, validate=validate_criteria)


class AnomalySchema(Schema):
    id = fields.Int(dump_only=True)
    meeting_name = fields.Str(required=True)
    datetime = fields.DateTime(required=True)
    anomaly_reason = JSONString(required=True)


class AnomalyRequestSchema(Schema):
    name = fields.Str(required=True)
    count = fields.Int(
        required=True, validate=Range(min=1, error="count must be positive")
    )


class ReportRequestSchema(Schema):
    start_datetime = fields.DateTime()


anomaly_schema = AnomalySchema()
meeting_schema = MeetingSchema()
meeting_request_schema = MeetingRequestSchema()
anomaly_request_schema = AnomalyRequestSchema()
report_request_schema = ReportRequestSchema()
