import datetime
import enum
import uuid

import sqlalchemy as sa
from app.database import Base
from app.utils.categorization import get_categories_for_memory
from sqlalchemy import (
    JSON,
    UUID,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    event,
)
from sqlalchemy.orm import Session, relationship


def get_current_utc_time():
    """Get current UTC time"""
    return datetime.datetime.now(datetime.UTC)


class MemoryState(enum.Enum):
    active = "active"
    paused = "paused"
    archived = "archived"
    deleted = "deleted"


class User(Base):
    __tablename__ = "users"
    id = Column(UUID, primary_key=True, default=lambda: uuid.uuid4())
    user_id = Column(String, nullable=False, unique=True, index=True)
    name = Column(String, nullable=True, index=True)
    email = Column(String, unique=True, nullable=True, index=True)
    metadata_ = Column('metadata', JSON, default=dict)
    created_at = Column(DateTime, default=get_current_utc_time, index=True)
    updated_at = Column(DateTime,
                        default=get_current_utc_time,
                        onupdate=get_current_utc_time)

    apps = relationship("App", back_populates="owner")
    memories = relationship("Memory", back_populates="user")


class App(Base):
    __tablename__ = "apps"
    id = Column(UUID, primary_key=True, default=lambda: uuid.uuid4())
    owner_id = Column(UUID, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(String)
    metadata_ = Column('metadata', JSON, default=dict)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=get_current_utc_time, index=True)
    updated_at = Column(DateTime,
                        default=get_current_utc_time,
                        onupdate=get_current_utc_time)

    owner = relationship("User", back_populates="apps")
    memories = relationship("Memory", back_populates="app")

    __table_args__ = (
        sa.UniqueConstraint('owner_id', 'name', name='idx_app_owner_name'),
    )


class Config(Base):
    __tablename__ = "configs"
    id = Column(UUID, primary_key=True, default=lambda: uuid.uuid4())
    key = Column(String, unique=True, nullable=False, index=True)
    value = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=get_current_utc_time)
    updated_at = Column(DateTime,
                        default=get_current_utc_time,
                        onupdate=get_current_utc_time)


class Memory(Base):
    __tablename__ = "memories"
    id = Column(UUID, primary_key=True, default=lambda: uuid.uuid4())
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False, index=True)
    app_id = Column(UUID, ForeignKey("apps.id"), nullable=False, index=True)
    content = Column(String, nullable=False)
    vector = Column(String)
    metadata_ = Column('metadata', JSON, default=dict)
    state = Column(Enum(MemoryState), default=MemoryState.active, index=True)
    created_at = Column(DateTime, default=get_current_utc_time, index=True)
    updated_at = Column(DateTime,
                        default=get_current_utc_time,
                        onupdate=get_current_utc_time)
    archived_at = Column(DateTime, nullable=True, index=True)
    deleted_at = Column(DateTime, nullable=True, index=True)

    user = relationship("User", back_populates="memories")
    app = relationship("App", back_populates="memories")
    categories = relationship("Category", secondary="memory_categories", back_populates="memories")

    __table_args__ = (
        Index('idx_memory_user_state', 'user_id', 'state'),
        Index('idx_memory_app_state', 'app_id', 'state'),
        Index('idx_memory_user_app', 'user_id', 'app_id'),
    )


class Category(Base):
    __tablename__ = "categories"
    id = Column(UUID, primary_key=True, default=lambda: uuid.uuid4())
    name = Column(String, unique=True, nullable=False, index=True)
    description = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.now(datetime.UTC), index=True)
    updated_at = Column(DateTime,
                        default=get_current_utc_time,
                        onupdate=get_current_utc_time)

    memories = relationship("Memory", secondary="memory_categories", back_populates="categories")

memory_categories = Table(
    "memory_categories", Base.metadata,
    Column("memory_id", UUID, ForeignKey("memories.id"), primary_key=True, index=True),
    Column("category_id", UUID, ForeignKey("categories.id"), primary_key=True, index=True),
    Index('idx_memory_category', 'memory_id', 'category_id')
)


class AccessControl(Base):
    __tablename__ = "access_controls"
    id = Column(UUID, primary_key=True, default=lambda: uuid.uuid4())
    subject_type = Column(String, nullable=False, index=True)
    subject_id = Column(UUID, nullable=True, index=True)
    object_type = Column(String, nullable=False, index=True)
    object_id = Column(UUID, nullable=True, index=True)
    effect = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=get_current_utc_time, index=True)

    __table_args__ = (
        Index('idx_access_subject', 'subject_type', 'subject_id'),
        Index('idx_access_object', 'object_type', 'object_id'),
    )


class ArchivePolicy(Base):
    __tablename__ = "archive_policies"
    id = Column(UUID, primary_key=True, default=lambda: uuid.uuid4())
    criteria_type = Column(String, nullable=False, index=True)
    criteria_id = Column(UUID, nullable=True, index=True)
    days_to_archive = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=get_current_utc_time, index=True)

    __table_args__ = (
        Index('idx_policy_criteria', 'criteria_type', 'criteria_id'),
    )


class MemoryStatusHistory(Base):
    __tablename__ = "memory_status_history"
    id = Column(UUID, primary_key=True, default=lambda: uuid.uuid4())
    memory_id = Column(UUID, ForeignKey("memories.id"), nullable=False, index=True)
    changed_by = Column(UUID, ForeignKey("users.id"), nullable=False, index=True)
    old_state = Column(Enum(MemoryState), nullable=False, index=True)
    new_state = Column(Enum(MemoryState), nullable=False, index=True)
    changed_at = Column(DateTime, default=get_current_utc_time, index=True)

    __table_args__ = (
        Index('idx_history_memory_state', 'memory_id', 'new_state'),
        Index('idx_history_user_time', 'changed_by', 'changed_at'),
    )


class MemoryAccessLog(Base):
    __tablename__ = "memory_access_logs"
    id = Column(UUID, primary_key=True, default=lambda: uuid.uuid4())
    memory_id = Column(UUID, ForeignKey("memories.id"), nullable=False, index=True)
    app_id = Column(UUID, ForeignKey("apps.id"), nullable=False, index=True)
    accessed_at = Column(DateTime, default=get_current_utc_time, index=True)
    access_type = Column(String, nullable=False, index=True)
    metadata_ = Column('metadata', JSON, default=dict)

    __table_args__ = (
        Index('idx_access_memory_time', 'memory_id', 'accessed_at'),
        Index('idx_access_app_time', 'app_id', 'accessed_at'),
    )

def categorize_memory(memory: Memory, db: Session) -> None:
    """Categorize a memory using OpenAI and store the categories in the database."""
    try:
        # Get categories from OpenAI
        categories = get_categories_for_memory(memory.content)

        # Get or create categories in the database
        for category_name in categories:
            category = db.query(Category).filter(Category.name == category_name).first()
            if not category:
                category = Category(
                    name=category_name,
                    description=f"Automatically created category for {category_name}"
                )
                db.add(category)
                db.flush()  # Flush to get the category ID

            # Check if the memory-category association already exists
            existing = db.execute(
                memory_categories.select().where(
                    (memory_categories.c.memory_id == memory.id) &
                    (memory_categories.c.category_id == category.id)
                )
            ).first()

            if not existing:
                # Create the association
                db.execute(
                    memory_categories.insert().values(
                        memory_id=memory.id,
                        category_id=category.id
                    )
                )

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error categorizing memory: {e}")


@event.listens_for(Memory, 'after_insert')
def after_memory_insert(mapper, connection, target):
    """Trigger categorization after a memory is inserted."""
    db = Session(bind=connection)
    categorize_memory(target, db)
    db.close()


@event.listens_for(Memory, 'after_update')
def after_memory_update(mapper, connection, target):
    """Trigger categorization after a memory is updated."""
    db = Session(bind=connection)
    categorize_memory(target, db)
    db.close()


# ===== SIGMA AGENT SYSTEM MODELS =====

class Project(Base):
    """Project being analyzed and improved by SIGMA agents"""
    __tablename__ = "projects"
    
    project_id = Column(Integer, primary_key=True, autoincrement=True)
    repo_url = Column(String, nullable=False)
    branch = Column(String, default='main')
    workspace_path = Column(String, nullable=False)
    language = Column(String, index=True)
    framework = Column(String, index=True)
    domain = Column(String, index=True)
    created_at = Column(DateTime, default=get_current_utc_time, index=True)
    last_analyzed = Column(DateTime, nullable=True, index=True)


class CodeSnapshot(Base):
    """Snapshot of code analysis results"""
    __tablename__ = "code_snapshots"
    
    snapshot_id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.project_id"), nullable=False, index=True)
    complexity = Column(sa.Float, default=0.0)
    test_coverage = Column(sa.Float, default=0.0)
    issues_found = Column(Integer, default=0)
    metrics_json = Column(String)
    created_at = Column(DateTime, default=get_current_utc_time, index=True)


class Proposal(Base):
    """Code improvement proposal from Dream Worker"""
    __tablename__ = "proposals"
    
    proposal_id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.project_id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(String)
    agents_json = Column(String)
    changes_json = Column(String)
    confidence = Column(sa.Float, default=0.0)
    critic_score = Column(sa.Float, default=0.0)
    status = Column(String, default='pending', index=True)
    pr_url = Column(String, nullable=True)
    commit_sha = Column(String, nullable=True)
    created_at = Column(DateTime, default=get_current_utc_time, index=True)
    executed_at = Column(DateTime, nullable=True, index=True)


class Experiment(Base):
    """Experiment conducted by DreamerMetaAgent"""
    __tablename__ = "experiments"
    
    experiment_id = Column(Integer, primary_key=True, autoincrement=True)
    worker_name = Column(String, nullable=False, index=True)
    experiment_name = Column(String, nullable=False)
    hypothesis = Column(String)
    approach = Column(String)
    baseline_metrics = Column(String)
    result_metrics = Column(String)
    success = Column(Boolean, nullable=True, index=True)
    improvement = Column(sa.Float, nullable=True)
    promoted_to_production = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=get_current_utc_time, index=True)
    completed_at = Column(DateTime, nullable=True, index=True)


class LearnedPattern(Base):
    """Patterns learned from successful proposals"""
    __tablename__ = "learned_patterns"
    
    pattern_id = Column(Integer, primary_key=True, autoincrement=True)
    pattern_name = Column(String, nullable=False)
    pattern_type = Column(String, nullable=False, index=True)
    description = Column(String)
    code_template = Column(String)
    language = Column(String, nullable=False, index=True)
    framework = Column(String, nullable=True, index=True)
    domain = Column(String, nullable=True, index=True)
    confidence = Column(sa.Float, default=0.0)
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=get_current_utc_time, index=True)
    last_used = Column(DateTime, nullable=True, index=True)


class CrossProjectLearning(Base):
    """Cross-project learning opportunities"""
    __tablename__ = "cross_project_learnings"
    
    learning_id = Column(Integer, primary_key=True, autoincrement=True)
    source_project_id = Column(Integer, ForeignKey("projects.project_id"), nullable=False, index=True)
    target_project_id = Column(Integer, ForeignKey("projects.project_id"), nullable=False, index=True)
    pattern_id = Column(Integer, ForeignKey("learned_patterns.pattern_id"), nullable=False, index=True)
    similarity_score = Column(sa.Float, default=0.0)
    applied = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=get_current_utc_time, index=True)
    applied_at = Column(DateTime, nullable=True, index=True)


class WorkerStats(Base):
    """Statistics for worker performance tracking"""
    __tablename__ = "worker_stats"
    
    stat_id = Column(Integer, primary_key=True, autoincrement=True)
    worker_name = Column(String, nullable=False, index=True)
    cycles_run = Column(Integer, default=0)
    experiments_run = Column(Integer, default=0)
    total_time = Column(sa.Float, default=0.0)
    errors = Column(Integer, default=0)
    last_run = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, default=get_current_utc_time, index=True)
