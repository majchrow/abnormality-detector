import pickle
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from pyod.models.hbos import HBOS


class Model:
    def __init__(self, name):
        self.name = name
        self.data = None
        self.model = None

    def _init_model(self):
        self.model = HBOS()

    def get_columns(self):
        return {
            # "datetime": datetime,
            "active_speaker": int,
            "connected": int,
            "endpoint_recording": int,
            "hour": int,
            "onhold": int,
            "presenter": int,
            "initial": int,
            "ringing": int,
            "week_day_number": int,
            "current_participants": int,
            "forwarding": int,
            "locked": int,
            "adhoc": int,
            "max_participants": int,
            "mean_participants": int,
            "recording": int,
            "streaming": int,
            "time_diff": float
        }

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, data):
        self._data = data

    def train(self):
        assert self.data is not None, "Cannot train model, without data set"
        self._init_model()
        self.model.fit(self.data, None)

    def predict(self, batch):
        assert self.model is not None, "Cannot predict batch without training model"
        return self.model.predict_proba(batch)

    def _generate_synthetic(self, samples=10000):
        columns = self.get_columns()
        data = {}
        for key, type in columns.items():
            value = None
            if type == int:
                value = np.random.randint(0, 2, size=samples)
            elif type == float:
                value = np.random.uniform(0, 40, size=samples)
            elif type == datetime:  # datetime, we should use it as day, week, year etc
                base = datetime(2000, 1, 1)
                value = np.array([base + timedelta(hours=i) for i in range(samples)])

            assert value is not None, f"Wrong type provided: {type}"
            data[key] = value

        return data

    def run_synthetic(self):
        data = self._generate_synthetic(samples=100000)
        pandas_data = pd.DataFrame(data)
        self.data = pandas_data
        self.train()
        test_data = self._generate_synthetic(samples=10)
        pandas_test_data = pd.DataFrame(test_data)
        # anomalies = self.predict(pandas_test_data)
        # print(f"[{self.name}] Predicted: ")
        # print(anomalies)
        self.serialize('new')
        self.deserialize('new')
        anomalies = self.predict(pandas_test_data)
        print(f"[{self.name}] Predicted: ")
        print(anomalies)

    def serialize(self, name):
        with open(name + '.pkl', 'wb') as clf:
            pickle.dump(self.model, clf)

    def deserialize(self, name):
        with open(name + '.pkl', 'rb') as clf:
            self.model = pickle.load(clf)


if __name__ == '__main__':
    model = Model("Chemia")
    model.run_synthetic()
