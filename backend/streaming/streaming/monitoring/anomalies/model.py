import numpy as np
import pandas as pd
import pickle as pkl

from datetime import datetime, timedelta
from pyod.models.hbos import HBOS


class Model:
    def __init__(self, meeting_name):
        self.meeting_name = meeting_name
        self.model = None

    def _init_model(self):
        self.model = HBOS()

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
            "time_diff",
        }

    def serialize(self):
        return pkl.dumps(self.model)

    def deserialize(self, serialized):
        self.model = pkl.loads(serialized)

    def train(self, data):
        self._init_model()
        self.model.fit(data, None)

    def predict(self, batch):
        assert self.model is not None, "Cannot predict batch without training model"
        return self.model.predict_proba(batch)
