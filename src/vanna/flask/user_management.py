from sqlalchemy import Column, String, DateTime, Boolean, Integer, ForeignKey, Table
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Optional, List, Dict
from .db_models import Base, APIKey

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    azure_id = Column(String(200), unique=True, nullable=False)
    email = Column(String(200), unique=True, nullable=False)
    name = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    is_active = Column(Boolean, default=True)
    
    # User type: 'admin', 'power_user', 'user'
    role = Column(String(50), nullable=False, default='user')
    
    # Relationships
    api_keys = relationship('APIKey', back_populates='user')
    
    # Permissions
    can_create_api_keys = Column(Boolean, default=False)
    can_view_audit_logs = Column(Boolean, default=False)
    can_manage_users = Column(Boolean, default=False)
    api_rate_limit = Column(Integer, default=100)  # Requests per minute

class UserManager:
    def __init__(self, session_factory):
        """
        Initialize user manager.
        
        Args:
            session_factory: SQLAlchemy session factory
        """
        self.Session = session_factory
    
    def get_or_create_user(self, azure_user_info: Dict) -> User:
        """
        Get existing user or create new one from Azure AD info.
        
        Args:
            azure_user_info: User info from Azure AD
        
        Returns:
            User object
        """
        session = self.Session()
        try:
            user = session.query(User).filter_by(
                azure_id=azure_user_info['id']
            ).first()
            
            if not user:
                # Create new user
                user = User(
                    azure_id=azure_user_info['id'],
                    email=azure_user_info.get('mail') or azure_user_info.get('userPrincipalName'),
                    name=azure_user_info.get('displayName'),
                    role=self._get_role_from_azure(azure_user_info)
                )
                session.add(user)
            
            # Update user info
            user.last_login = datetime.utcnow()
            user.name = azure_user_info.get('displayName', user.name)
            
            # Update permissions based on role
            self._update_user_permissions(user)
            
            session.commit()
            return user
            
        finally:
            session.close()
    
    def _get_role_from_azure(self, azure_user_info: Dict) -> str:
        """Map Azure AD roles to application roles"""
        azure_roles = azure_user_info.get('roles', [])
        
        if 'Admin' in azure_roles:
            return 'admin'
        elif 'PowerUser' in azure_roles:
            return 'power_user'
        return 'user'
    
    def _update_user_permissions(self, user: User):
        """Update user permissions based on role"""
        if user.role == 'admin':
            user.can_create_api_keys = True
            user.can_view_audit_logs = True
            user.can_manage_users = True
            user.api_rate_limit = 1000
        elif user.role == 'power_user':
            user.can_create_api_keys = True
            user.can_view_audit_logs = True
            user.can_manage_users = False
            user.api_rate_limit = 500
        else:  # regular user
            user.can_create_api_keys = False
            user.can_view_audit_logs = False
            user.can_manage_users = False
            user.api_rate_limit = 100
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        session = self.Session()
        try:
            return session.query(User).filter_by(id=user_id).first()
        finally:
            session.close()
    
    def get_user_by_azure_id(self, azure_id: str) -> Optional[User]:
        """Get user by Azure ID"""
        session = self.Session()
        try:
            return session.query(User).filter_by(azure_id=azure_id).first()
        finally:
            session.close()
    
    def list_users(self, page: int = 1, per_page: int = 50) -> List[User]:
        """List users with pagination"""
        session = self.Session()
        try:
            return session.query(User)\
                .order_by(User.created_at.desc())\
                .offset((page - 1) * per_page)\
                .limit(per_page)\
                .all()
        finally:
            session.close()
    
    def update_user_role(self, user_id: int, new_role: str) -> bool:
        """Update user role and permissions"""
        session = self.Session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                return False
            
            user.role = new_role
            self._update_user_permissions(user)
            session.commit()
            return True
        finally:
            session.close()
    
    def deactivate_user(self, user_id: int) -> bool:
        """Deactivate user and their API keys"""
        session = self.Session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                return False
            
            user.is_active = False
            # Deactivate all user's API keys
            for key in user.api_keys:
                key.is_active = False
            
            session.commit()
            return True
        finally:
            session.close()
    
    def get_user_api_keys(self, user_id: int) -> List[APIKey]:
        """Get all API keys for a user"""
        session = self.Session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            return user.api_keys if user else []
        finally:
            session.close()

# Update APIKey model to include user relationship
APIKey.user_id = Column(Integer, ForeignKey('users.id'))
APIKey.user = relationship('User', back_populates='api_keys') 