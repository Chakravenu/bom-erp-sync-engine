"""
Data models for BOM synchronization
Simple dataclasses for clean data handling
"""
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


@dataclass
class BOMPart:
    """Represents a single part in the BOM hierarchy"""
    id: str
    part_number: str
    description: str
    category: Optional[str] = None
    quantity: int = 1
    unit_price: float = 0.0
    bom_level: int = 0
    parent_assembly: Optional[str] = None
    is_assembly: bool = False
    supplier: Optional[str] = None
    children: List["BOMPart"] = field(default_factory=list)


@dataclass
class SyncResult:
    """Result of a synchronization operation"""
    version: str
    total_parts: int = 0
    inserted: int = 0
    updated: int = 0
    errors: int = 0
    error_messages: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "pending"
    
    def to_dict(self):
        return {
            "version": self.version,
            "total_parts": self.total_parts,
            "inserted": self.inserted,
            "updated": self.updated,
            "errors": self.errors,
            "error_messages": self.error_messages,
            "duration_seconds": round(self.duration_seconds, 3),
            "timestamp": self.timestamp,
            "status": self.status
        }


@dataclass
class BOMVersion:
    """BOM version information"""
    version_id: int
    version_number: str
    description: str
    created_at: str
    is_active: bool
    total_cost: float = 0.0
    part_count: int = 0