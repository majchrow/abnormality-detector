from flask_cors import cross_origin
from flask_restful import Resource, Api
from flask import request
from marshmallow import ValidationError

from .db import dao
from .bridge import dao as bridge_dao
from .exceptions import NotFoundError
from .schema import anomaly_schema, anomaly_request_schema, meeting_schema, meeting_request_schema


class Meetings(Resource):
    # TODO: this method should belong to separate Conferences resource
    @cross_origin()
    def get(self):
        result = dao.get_conferences()
        result['created'] = list(map(meeting_schema.dump, result['created']))
        return result

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
            dao.remove_meeting(name)
            return {"message": f"successfully removed {name} from monitored conferences"}, 200
        except NotFoundError:
            return {"message": f"no meeting {name}"}, 404


class MeetingDetails(Resource):
    @cross_origin()
    def get(self, conf_name):
        if meeting := dao.meeting_details(conf_name):
            return meeting
        else:
            return {"message": f"no meeting {conf_name}"}, 404


class Anomalies(Resource):
    @cross_origin()
    def get(self):
        try:
            if errors := anomaly_request_schema.validate(request.args.to_dict()):
                return {"message": f'invalid request: {errors}'}, 400

            conf_name, count = request.args['name'], int(request.args['count'])
            result = dao.get_anomalies(conf_name, count)
            result['anomalies'] = list(map(anomaly_schema.dump, result['anomalies']))
            return result
        except NotFoundError:
            return {"message": f"no meeting {conf_name}"}, 404


class BridgeMeetings(Resource):
    @cross_origin()
    def get(self): 
        return {'meetings': bridge_dao.get_meetings()}


def setup_resources(app):
    api = Api(app)
    api.add_resource(Meetings, "/conferences")
    api.add_resource(MeetingDetails, "/conferences/<string:conf_name>")
    api.add_resource(Anomalies, "/anomalies")
    api.add_resource(BridgeMeetings, "/meetings")

