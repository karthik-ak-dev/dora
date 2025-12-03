"""
Authentication service.
Business logic for user authentication and registration.
"""
from datetime import timedelta
from sqlalchemy.orm import Session

from ..repositories.user_repository import UserRepository
from ..utils.security import SecurityUtils
from ..utils.exceptions import DuplicateResourceError, AuthenticationError
from ...config.settings import settings


class AuthService:
    """Service for authentication-related business logic."""
    
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
    
    def register_user(self, email: str, password: str) -> tuple:
        """
        Register a new user.
        
        Args:
            email: User's email address
            password: Plain text password
            
        Returns:
            Tuple of (user, access_token, expires_in)
            
        Raises:
            DuplicateResourceError: If email already exists
        """
        # Check if email already exists
        if self.user_repo.email_exists(email):
            raise DuplicateResourceError("Email already registered")
        
        # Hash password
        password_hash = SecurityUtils.hash_password(password)
        
        # Create user
        user = self.user_repo.create(
            email=email,
            password_hash=password_hash
        )
        
        # Generate JWT token
        access_token = SecurityUtils.create_access_token(
            data={"user_id": str(user.id), "email": user.email},
            secret_key=settings.SECRET_KEY,
            expires_delta=timedelta(seconds=settings.JWT_EXPIRY_SECONDS)
        )
        
        return user, access_token, settings.JWT_EXPIRY_SECONDS
    
    def login_user(self, email: str, password: str) -> tuple:
        """
        Authenticate user and generate token.
        
        Args:
            email: User's email address
            password: Plain text password
            
        Returns:
            Tuple of (user, access_token, expires_in)
            
        Raises:
            AuthenticationError: If credentials are invalid
        """
        # Get user by email
        user = self.user_repo.get_by_email(email)
        if not user:
            raise AuthenticationError("Invalid email or password")
        
        # Verify password
        if not SecurityUtils.verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid email or password")
        
        # Generate JWT token
        access_token = SecurityUtils.create_access_token(
            data={"user_id": str(user.id), "email": user.email},
            secret_key=settings.SECRET_KEY,
            expires_delta=timedelta(seconds=settings.JWT_EXPIRY_SECONDS)
        )
        
        return user, access_token, settings.JWT_EXPIRY_SECONDS
