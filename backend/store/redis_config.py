import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Redis Cloud configuration
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', '')
REDIS_DB = int(os.getenv('REDIS_DB', '0'))

def get_redis_config():
    """Get Redis configuration from environment variables."""
    return {
        'host': REDIS_HOST,
        'port': REDIS_PORT,
        'password': REDIS_PASSWORD,
        'db': REDIS_DB
    } 