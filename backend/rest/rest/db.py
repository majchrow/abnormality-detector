from flask_cassandra import CassandraCluster


class CassandraDAO:
    def __init__(self, engine=None):
        self.engine = engine

    def init(self, engine):
        self.engine = engine

    def get_conferences(self):
        return [{'id': 42, 'name': 'stuff'}]

    def conference_details(self, conf_id):
        return {
            'id': conf_id,
            'name': 'stuff',
            'num_participants': 42
        }


dao = CassandraDAO()


def setup_db(app):
    cassandra = CassandraCluster()
    cassandra.init_app(app)
    dao.init(cassandra)
