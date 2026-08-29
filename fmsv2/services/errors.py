class ValidationError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


class NotFoundError(Exception):
    pass


class ConflictError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


class ExternalServiceError(Exception):
    def __init__(self, message, status=502):
        super().__init__(message)
        self.message = message
        self.status = status
