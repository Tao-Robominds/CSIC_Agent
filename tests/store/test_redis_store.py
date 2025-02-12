import pytest
from backend.store.redis_store import RedisStore, Memory
from backend.store.redis_config import get_redis_config

@pytest.fixture
def redis_store():
    config = get_redis_config()
    return RedisStore(**config)

def test_redis_connection(redis_store):
    """Test basic Redis connection"""
    try:
        redis_store.redis.ping()
        assert True
    except Exception as e:
        pytest.fail(f"Redis connection failed: {str(e)}")

def test_store_operations(redis_store):
    """Test basic store operations"""
    # Test data
    namespace = ("test", "user1")
    key = "test_key"
    value = {"message": "test value"}
    
    # Test put
    redis_store.put(namespace, key, value)
    
    # Test get
    result = redis_store.get(namespace, key)
    assert isinstance(result, Memory)
    assert result.value == value
    
    # Test search
    memories = redis_store.search(namespace)
    assert len(memories) > 0
    assert any(mem.key == key for mem in memories)
    
    # Test delete
    redis_store.delete(namespace, key)
    assert redis_store.get(namespace, key) is None

def test_json_serialization(redis_store):
    """Test storing and retrieving complex JSON data"""
    namespace = ("test", "user1")
    key = "json_test"
    value = {
        "string": "test",
        "number": 42,
        "list": [1, 2, 3],
        "nested": {"key": "value"}
    }
    
    redis_store.put(namespace, key, value)
    result = redis_store.get(namespace, key)
    assert result.value == value
    
    redis_store.delete(namespace, key) 