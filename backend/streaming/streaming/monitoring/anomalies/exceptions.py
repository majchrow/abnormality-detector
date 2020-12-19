class MissingDataError(Exception):
    """Attempted training or inference on empty dataset."""
    pass


class MissingModelError(Exception):
    """Attempted inference with non-existing model."""
    pass
