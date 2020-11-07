from flask_cors import cross_origin
from flask_restful import Resource, Api

from .db import dao


class Conferences(Resource):
    @cross_origin()
    def get(self):
        conferences = dao.get_conferences()
        # TODO: specify serialization?
        return {'current': conferences, 'recent': []}


class ConferenceDetails(Resource):
    @cross_origin()
    def get(self, conf_id):
        # TODO: specify serialization?
        return dao.conference_details(conf_id)


def setup_resources(app):
    api = Api(app)
    api.add_resource(Conferences, '/conferences')
    api.add_resource(ConferenceDetails, '/conferences/<string:conf_id>')
