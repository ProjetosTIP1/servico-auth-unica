class AuthException(Exception):
    """Base exception for authentication errors"""

    def __init__(self, message: str, status_code: int = 401):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class SecurityBreachException(AuthException):
    """Exception raised when a potential security breach is detected (e.g., token reuse)"""

    def __init__(
        self,
        message: str = "Refresh token reuse detected. All tokens revoked for security.",
    ):
        super().__init__(message, status_code=403)


class InvalidCredentialsException(AuthException):
    """Exception raised when invalid credentials are provided"""

    def __init__(self, message: str = "Invalid username or password"):
        super().__init__(message, status_code=401)


class TokenRevokedException(AuthException):
    """Exception raised when a revoked token is used"""

    def __init__(self, message: str = "Token has been revoked"):
        super().__init__(message, status_code=401)


class UserNotFoundException(AuthException):
    """Exception raised when a user is not found"""

    def __init__(self, message: str = "User not found"):
        super().__init__(message, status_code=404)
