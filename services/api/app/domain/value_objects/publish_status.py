from enum import Enum


class PublishStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"
    LIVE = "live"
    ARCHIVED = "archived"
