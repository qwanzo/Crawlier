"""
Conftest for pytest — shared fixtures and configuration.
"""

import pytest
import tempfile
import os


@pytest.fixture
def temp_db():
    """Provide a temporary database for testing."""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_file.close()
    yield temp_file.name
    if os.path.exists(temp_file.name):
        os.remove(temp_file.name)


@pytest.fixture
def temp_output_dir():
    """Provide a temporary output directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup
    import shutil
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.fixture
def sample_html():
    """Provide sample HTML for testing."""
    return """
    <html>
        <head>
            <title>Test Page</title>
            <meta name="description" content="A test page">
            <meta name="keywords" content="test, sample, html">
        </head>
        <body>
            <h1>Welcome</h1>
            <p>This is a test paragraph with email test@example.com and phone 555-1234.</p>
            <a href="https://facebook.com/testpage">Facebook</a>
            <a href="https://twitter.com/testuser">Twitter</a>
            <img src="/image.png" alt="Test Image">
            <form action="/submit" method="POST">
                <input type="text" name="username" required>
                <input type="email" name="email">
                <button type="submit">Submit</button>
            </form>
        </body>
    </html>
    """


@pytest.fixture
def sample_response():
    """Provide a mock HTTP response."""
    from unittest.mock import MagicMock
    response = MagicMock()
    response.status_code = 200
    response.headers = {
        'Content-Type': 'text/html; charset=utf-8',
        'Server': 'nginx/1.21.0'
    }
    response.text = """
    <html>
        <head><title>Test</title></head>
        <body><p>Test content</p></body>
    </html>
    """
    response.content = response.text.encode('utf-8')
    response.elapsed.total_seconds.return_value = 0.5
    response.history = []
    return response
