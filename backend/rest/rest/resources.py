from flask_cors import cross_origin
from flask_restful import Resource, Api
from flask import current_app, request

from .db import dao


class Conferences(Resource):
    @cross_origin()
    def get(self):
        return dao.get_conferences()

    @cross_origin()
    def post(self):
        if not request.json or "name" not in request.json:
            return {"message": "invalid body"}, 400
        name = request.json["name"]
        dao.add_to_monitored(name)
        return {"message": f"successfully added {name} to monitored conferences"}, 201

    @cross_origin()
    def delete(self):
        if not request.json or "name" not in request.json:
            return {"message": "invalid body"}, 400
        name = request.json["name"]
        dao.remove_from_monitored(name)
        return {
            "message": f"successfully removed {name} from monitored conferences"
        }, 200


class ConferenceDetails(Resource):
    @cross_origin()
    def get(self, conf_id):
        return dao.conference_details(conf_id)


def setup_resources(app):
    api = Api(app)
    api.add_resource(Conferences, "/conferences")
    api.add_resource(ConferenceDetails, "/conferences/<string:conf_id>")
