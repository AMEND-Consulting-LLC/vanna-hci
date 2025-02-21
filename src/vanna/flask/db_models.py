from sqlalchemy import create_engine, Column, String, DateTime, Boolean, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

Base = declarative_base()

class APIKey(Base):
    __tablename__ = 'api_keys'
    
    id = Column(Integer, primary_key=True)
    key = Column(String(64), unique=True, nullable=False, index=True)
    role = Column(String(20), nullable=False)
    description = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime)
    expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
    created_by = Column(String(200))  # Azure AD user ID who created the key

class KeyAuditLog(Base):
    __tablename__ = 'key_audit_log'
    
    id = Column(Integer, primary_key=True)
    api_key_id = Column(Integer, nullable=False)
    event_type = Column(String(50), nullable=False)  # created, used, revoked, etc.
    timestamp = Column(DateTime, default=datetime.utcnow)
    details = Column(String(500))
    ip_address = Column(String(45))  # IPv6-compatible length

def init_db(app_config):
    """Initialize database connection and create tables"""
    database_url = app_config.get('DATABASE_URL', os.getenv('DATABASE_URL', 'sqlite:///data/api_keys.db'))
    
    # Create engine
    engine = create_engine(database_url)
    
    # Create tables
    Base.metadata.create_all(engine)
    
    # Create session factory
    Session = sessionmaker(bind=engine)
    
    return Session

def create_initial_admin_key(session, admin_key):
    """Create initial admin API key if none exists"""
    existing_admin = session.query(APIKey).filter_by(role='admin').first()
    if not existing_admin:
        admin_api_key = APIKey(
            key=admin_key,
            role='admin',
            description='Initial admin API key',
            created_by='system'
        )
        session.add(admin_api_key)
        session.commit() 