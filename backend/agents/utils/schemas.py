from datetime import datetime
from typing import Literal, Optional, List
from pydantic import BaseModel, Field

class Command(BaseModel):
    """This is the command of the user you are chatting with"""
    name: Optional[str] = Field(description="The user's name", default="Jack")
    location: Optional[str] = Field(description="The user's location", default="London")
    job: Optional[str] = Field(description="The user's job", default="Chairman")
    connections: list[str] = Field(
        description="Business connections of the user, such as CEO, CMO, CFO, etc.",
        default_factory=list
    )
    interests: list[str] = Field(
        description="Buesiness interests that the user has", 
        default_factory=list
    )

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