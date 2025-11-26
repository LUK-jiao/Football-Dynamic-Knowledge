"""
Pydantic schemas for data source related operations.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl


class CrawlerType(str, Enum):
    """Types of crawlers."""
    WEB = "web"
    API = "api"
    RSS = "rss"


class CrawlerConfig(BaseModel):
    """Crawler configuration schema."""
    id: Optional[str] = None
    name: str = Field(..., description="Crawler name")
    type: CrawlerType
    url: HttpUrl
    schedule: Optional[str] = Field(None, description="Cron expression for scheduling")
    config: Dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True
    created_at: Optional[datetime] = None


class CrawlTask(BaseModel):
    """Crawl task schema."""
    id: Optional[str] = None
    crawler_id: str
    status: str = "pending"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class CrawlStatus(BaseModel):
    """Crawl task status schema."""
    task_id: str
    status: str
    progress: float = Field(0.0, ge=0.0, le=1.0)
    items_collected: int = 0
    message: Optional[str] = None
