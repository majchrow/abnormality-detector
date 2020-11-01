from flask import Flask
from flask_restful import Resource, Api
from flask_cors import CORS, cross_origin

app = Flask(__name__)
api = Api(app)
CORS(app)


@api.resource('/meetings')
class Meetings(Resource):
    @cross_origin()
    def get(self):
        return {'meetings': ['a', 'b']}


if __name__ == '__main__':
    app.run()
