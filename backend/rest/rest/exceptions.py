class AlreadyExistsError(Exception):
    """Attempted to create entity already present in the database"""
    pass


class NotFoundError(Exception):
    """Attempted to access entity not present in the database"""
    pass
