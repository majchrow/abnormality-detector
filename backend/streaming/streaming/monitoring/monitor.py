class Monitor:
    def __init__(self):
        self.criteria = None

    def set_criteria(self, criteria):
        self.criteria = criteria

    def verify(self, msg):
        return f'bob: {len(msg)}'
