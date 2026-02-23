import datetime
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    Text,
    ForeignKey,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    
    # User settings
    output_format = Column(String, default="markdown")
    template_type = Column(String, default="classic")
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    generations = relationship("Generation", back_populates="user")

    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, username='{self.username}')>"


class Generation(Base):
    __tablename__ = "generations"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    raw_text = Column(Text, nullable=False)
    generated_test_cases = Column(Text, nullable=False)
    
    output_format = Column(String, nullable=False)
    template_type = Column(String, nullable=False)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    user = relationship("User", back_populates="generations")

    def __repr__(self):
        return f"<Generation(id={self.id}, user_id={self.user_id}, created_at='{self.created_at}')>"


class ConversationHistory(Base):
    __tablename__ = "conversation_history"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    request = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    user = relationship("User")

    def __repr__(self):
        return f"<ConversationHistory(id={self.id}, user_id={self.user_id})>"
