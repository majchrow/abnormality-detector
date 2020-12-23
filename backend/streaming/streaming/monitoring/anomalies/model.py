import numpy as np
import pandas as pd
import pickle as pkl

from datetime import datetime, timedelta
from pyod.models.cblof import CBLOF
from pyod.models.hbos import HBOS
from pyod.models.knn import KNN
from pyod.models.lof import LOF
from pyod.models.ocsvm import OCSVM


class Model:
    models = [OCSVM, HBOS, CBLOF, LOF, KNN]

    def __init__(self, meeting_name):
        self.meeting_name = meeting_name
        self.model = None
        self.model_cls = Model.models[1]

    def _init_model(self):
        self.model = self.model_cls()

    @staticmethod
    def get_columns():
        return {
            "datetime",
            "active_speaker",
            "connected",
            "endpoint_recording",
            "hour",
            "onhold",
            "presenter",
            "initial",
            "ringing",
            "week_day_number",
            "current_participants",
            "forwarding",
            "locked",
            "adhoc",
            "max_participants",
            "mean_participants",
            "recording",
            "streaming",
            # "time_diff",
        }

    def serialize(self):
        return pkl.dumps(self.model)

    def deserialize(self, serialized):
        self.model = pkl.loads(serialized)

    def train(self, data):
        self._init_model()
        self.model.fit(data, None)

    def predict(self, batch):
        if not batch.empty:
            # IsolationForest has decision_function - but values are weird
            # predictions = self.model.decision_function(batch)
            predictions = self.model.predict_proba(batch)[:, 1]
            return pd.DataFrame(predictions, index=batch.index, columns=['score'])
        else:
            return pd.DataFrame([], columns=['score'])
