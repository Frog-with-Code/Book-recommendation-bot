class ApplicationError(Exception):
    pass


class UserNotFoundError(ApplicationError):
    pass


class BookNotFoundError(ApplicationError):
    pass


class UserAlreadyExistsError(ApplicationError):
    pass


class RecommendationsExhaustedError(ApplicationError):
    pass
