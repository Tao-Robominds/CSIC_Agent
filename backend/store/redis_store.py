from typing import Any, Dict, List, Optional, Tuple, NamedTuple, AsyncIterator, Iterator
import json
import redis
from langgraph.store.base import BaseStore

class Memory(NamedTuple):
    """Memory object to store key-value pairs with namespace."""
    namespace: Tuple
    key: str
    value: Dict

class RedisStore(BaseStore):
    """Redis implementation of BaseStore for persistence."""
    
    def __init__(self, host: str, port: int, password: str, db: int = 0):
        """Initialize Redis connection."""
        self.redis = redis.Redis(
            host=host,
            port=port,
            password=password,
            db=db,
            decode_responses=True
        )
        
    def _make_key(self, namespace: Tuple, key: str) -> str:
        """Create a Redis key from namespace and key."""
        return f"{':'.join(namespace)}:{key}"
        
    def get(self, namespace: Tuple, key: str) -> Optional[Memory]:
        """Get a value from Redis."""
        redis_key = self._make_key(namespace, key)
        value = self.redis.get(redis_key)
        if value is None:
            return None
        return Memory(namespace=namespace, key=key, value=json.loads(value))
        
    def put(self, namespace: Tuple, key: str, value: Dict) -> None:
        """Put a value into Redis."""
        redis_key = self._make_key(namespace, key)
        self.redis.set(redis_key, json.dumps(value))
        
    def delete(self, namespace: Tuple, key: str) -> None:
        """Delete a value from Redis."""
        redis_key = self._make_key(namespace, key)
        self.redis.delete(redis_key)
        
    def search(self, namespace: Tuple) -> List[Memory]:
        """Search for all values in a namespace."""
        pattern = f"{':'.join(namespace)}:*"
        keys = self.redis.keys(pattern)
        memories = []
        for redis_key in keys:
            key = redis_key.split(":")[-1]  # Get the original key
            value = self.redis.get(redis_key)
            if value:
                memories.append(Memory(
                    namespace=namespace,
                    key=key,
                    value=json.loads(value)
                ))
        return memories

    def batch(self, operations: List[Tuple[str, Tuple, str, Optional[Dict]]]) -> Iterator[Optional[Memory]]:
        """Execute batch operations."""
        results = []
        for op, namespace, key, value in operations:
            if op == "get":
                results.append(self.get(namespace, key))
            elif op == "put":
                self.put(namespace, key, value)
                results.append(None)
            elif op == "delete":
                self.delete(namespace, key)
                results.append(None)
        return iter(results)

    async def abatch(self, operations: List[Tuple[str, Tuple, str, Optional[Dict]]]) -> AsyncIterator[Optional[Memory]]:
        """Execute batch operations asynchronously."""
        # Since redis-py doesn't support async operations natively,
        # we'll just wrap the synchronous batch method
        for result in self.batch(operations):
            yield result 