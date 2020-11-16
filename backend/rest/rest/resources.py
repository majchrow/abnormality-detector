from flask_cors import cross_origin
from flask_restful import Resource, Api
from flask import request
from marshmallow import ValidationError

from .db import dao
from .exceptions import AlreadyExistsError, NotFoundError
from .schema import meeting_schema


class Conferences(Resource):
    @cross_origin()
    def get(self):
        return dao.get_conferences()

    @cross_origin()
    def post(self):
        json_data = request.get_json()
        if not json_data:
            return {"message": "No input data provided"}, 400
        try:
            data = meeting_schema.load(json_data)
        except ValidationError as err:
            return err.messages, 422

        try:
            dao.add_meeting(data['name'], data['criteria'])
            return {"message": f"successfully added {data['name']} to monitored conferences"}, 201
        except AlreadyExistsError:
            return {"message": "meeting already added"}, 400

    @cross_origin()
    def put(self):
        json_data = request.get_json()
        if not json_data:
            return {"message": "No input data provided"}, 400
        try:
            data = meeting_schema.load(json_data)
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
            return {"message": f"no meeting {name}"}, 400


class ConferenceDetails(Resource):
    @cross_origin()
    def get(self, conf_name):
        return dao.conference_details(conf_name)


def setup_resources(app):
    api = Api(app)
    api.add_resource(Conferences, "/conferences")
    api.add_resource(ConferenceDetails, "/conferences/<string:conf_name>")
