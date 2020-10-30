from flask import Flask
from flask_cors import CORS
from flask_restful import Resource, Api

app = Flask(__name__)
api = Api(app)
cors = CORS(app, resources={r"/*": {"origins": "*"}})


@api.resource('/')
class Foo(Resource):
    def get(self):
        return 'Hello, World!'


if __name__ == '__main__':
    app.run()