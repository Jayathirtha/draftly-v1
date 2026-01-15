"""
Pytest configuration and shared fixtures for draftly_v1 tests.
"""
import pytest
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

# Set required environment variables before importing app modules
os.environ['GROQ_API_KEY'] = 'test_groq_api_key_for_testing'
os.environ['DATABASE_URL'] = 'sqlite:///./test_draftly.db'

# Add src directory to path for imports
src_path = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(src_path))


@pytest.fixture(autouse=True)
def mock_chatgroq():
    """Mock ChatGroq LLM client to avoid API calls during tests"""
    with patch('draftly_v1.services.llm_services.ChatGroq') as mock_groq:
        mock_instance = MagicMock()
        mock_instance.invoke.return_value.content = 'Test AI generated draft response'
        mock_groq.return_value = mock_instance
        yield mock_instance


@pytest.fixture(autouse=True)
def mock_database_creation():
    """Mock database table creation to avoid actual DB operations during tests"""
    with patch('draftly_v1.services.database.Base.metadata.create_all'):
        yield


@pytest.fixture(autouse=True)
def reset_test_environment():
    """Reset environment before each test"""
    yield
    
    # Close all database connections
    from draftly_v1.services.database import engine
    if engine:
        engine.dispose()
    
    # Cleanup test database if it exists
    import time
    test_db = Path('test_draftly.db')
    if test_db.exists():
        # Retry a few times in case file is still locked
        for _ in range(3):
            try:
                test_db.unlink()
                break
            except PermissionError:
                time.sleep(0.1)


@pytest.fixture
def sample_email():
    """Sample email address for testing"""
    return 'test@example.com'


@pytest.fixture
def sample_thread_id():
    """Sample thread ID for testing"""
    return 'thread_test_123'


@pytest.fixture
def sample_draft_body():
    """Sample draft email body"""
    return '<p>This is a test draft email body.</p>'

