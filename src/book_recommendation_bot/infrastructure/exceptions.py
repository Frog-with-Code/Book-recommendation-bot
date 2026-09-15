class InfrastructureError(Exception):
    pass


class DBError(InfrastructureError):
    pass


class UniqueConstraintViolationError(DBError):
    pass


class RecordNotFoundError(DBError):
    pass
