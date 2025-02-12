from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class ToDo(BaseModel):
    """Todo item information."""
    task: str
    status: str = "Active"  # Can be "Active" or "Done"
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    solutions: List[str] = Field(default_factory=list)

    def model_dump(self, *args, **kwargs):
        """Custom dump method to handle datetime serialization."""
        data = super().model_dump(*args, **kwargs)
        # Convert datetime objects to ISO format strings only if they're datetime objects
        if isinstance(data.get('created_at'), datetime):
            data['created_at'] = data['created_at'].isoformat()
        if isinstance(data.get('completed_at'), datetime):
            data['completed_at'] = data['completed_at'].isoformat()
        return data

    def __str__(self):
        """String representation of the todo item."""
        return f"{self.task} ({self.status})" 