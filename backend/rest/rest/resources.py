from dateutil.parser import parse, ParserError
from flask_cors import cross_origin
from flask_restful import Resource, Api
from flask import request
from marshmallow import ValidationError

from .db import dao
from .bridge import dao as bridge_dao
from .exceptions import NotFoundError
from .schema import anomaly_schema, meeting_schema, meeting_request_schema


class Meetings(Resource):
    @cross_origin()
    def get(self):
        return {'meetings': bridge_dao.get_meetings()}

    @cross_origin()
    def put(self):
        json_data = request.get_json()
        if not json_data:
            return {"message": "No input data provided"}, 400
        try:
            data = meeting_request_schema.load(json_data)
        except ValidationError as err:
            return err.messages, 422

        dao.update_meeting(data['name'], data['criteria'])
        return {"message": f"successfully updated {data['name']}"}, 200

    @cross_origin()
    def delete(self):
        name = request.args.get("name", None)
        if not name:
            return {"message": f"conference to remove is not specified"}, 400

        try:
            dao.clear_meeting(name)
            return {"message": f"successfully removed {name} from monitored conferences"}, 200
        except NotFoundError:
            return {"message": f"no meeting {name}"}, 404


class MeetingDetails(Resource):
    @cross_origin()
    def get(self, meeting_name):
        if meeting := dao.meeting_details(meeting_name):
            return meeting
        else:
            return {"message": f"no meeting {meeting_name}"}, 404


class Calls(Resource):
    @cross_origin()
    def get(self):
        result = dao.get_conferences()
        result['created'] = list(map(meeting_schema.dump, result['created']))
        return result


class CallHistory(Resource):
    @cross_origin()
    def get(self, meeting_name):
        start_date = request.args.get("start", None)
        end_date = request.args.get("end", None)

        try:
            # TODO: timezone!
            if start_date:
                start_date = parse(start_date)
            if end_date:
                end_date = parse(end_date)
        except ParserError:
            return {"message": "invalid date format"}, 400

        result = dao.get_calls(meeting_name, start_date, end_date)
        return {'calls': result}


class Anomalies(Resource):
    @cross_origin()
    def get(self, meeting_name):
        start_date = request.args.get("start", None)
        end_date = request.args.get("end", None)

        try:
            # TODO: timezone!
            if start_date:
                start_date = parse(start_date)
            if end_date:
                end_date = parse(end_date)
        except ParserError:
            return {"message": "invalid date format"}, 400

        result = dao.get_anomalies(meeting_name, start_date, end_date)
        result['anomalies'] = list(map(anomaly_schema.dump, result['anomalies']))
        return result


def setup_resources(app):
    api = Api(app)
    api.add_resource(Meetings, "/meetings")
    api.add_resource(MeetingDetails, "/meetings/<string:meeting_name>")
    api.add_resource(Calls, "/calls")
    api.add_resource(CallHistory, "/calls/<string:meeting_name>")
    api.add_resource(Anomalies, "/anomalies/<string:meeting_name>")
