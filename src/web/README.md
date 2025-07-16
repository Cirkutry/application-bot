# Web Server Refactoring

This directory contains the refactored web server components that were previously all contained in the monolithic `webserver.py` file.

## Structure

```
src/web/
├── __init__.py
├── README.md
├── main.py              # Standalone web server entry point
├── server.py            # Main web server orchestration
├── config/
│   ├── __init__.py
│   └── settings.py      # Configuration and environment variables
├── middleware/
│   ├── __init__.py
│   ├── auth.py          # Authentication middleware
│   └── error.py         # Error handling middleware
├── auth/
│   ├── __init__.py
│   └── decorators.py    # Authentication decorators
├── routes/
│   ├── __init__.py
│   ├── auth.py          # Authentication routes (login, callback, logout)
│   ├── pages.py         # Page routes (dashboard, applications, etc.)
│   └── api.py           # API endpoints
└── utils/
    ├── __init__.py
    ├── logging.py       # Logging configuration
    ├── template_setup.py # Jinja2 template setup
    └── template_helpers.py # Template helper functions
```

## Key Improvements

### 1. **Modular Architecture**
- Separated concerns into focused modules
- Each module has a single responsibility
- Easier to maintain and test individual components

### 2. **Configuration Management**
- Centralized configuration in `config/settings.py`
- Environment variables and constants in one place
- Easy to modify settings without touching application logic

### 3. **Middleware Structure**
- Clean separation of authentication and error handling
- Reusable middleware components
- Better error handling and logging

### 4. **Route Organization**
- Routes grouped by functionality (auth, pages, API)
- Clear separation between page routes and API endpoints
- Easier to add new routes or modify existing ones

### 5. **Utility Functions**
- Template helpers separated from route logic
- Reusable utility functions
- Better code organization

## Usage

### With Discord Bot
The web server is automatically started when running the main bot:

```python
from src.web.server import start_web_server

# In your bot startup code
runner, site = await start_web_server(bot_instance)
```

### Standalone Testing
You can run the web server independently for testing:

```bash
python src/web/main.py
```

## Migration Notes

### From Old `webserver.py`
- All functionality has been preserved
- Routes maintain the same endpoints and behavior
- Authentication and middleware work identically
- Template rendering unchanged

### Environment Variables
The following environment variables are still required:
- `WEB_HOST` - Web server host (default: localhost)
- `WEB_PORT` - Web server port (default: 8080)
- `OAUTH_CLIENT_ID` - Discord OAuth client ID
- `OAUTH_CLIENT_SECRET` - Discord OAuth client secret
- `OAUTH_REDIRECT_URI` - Discord OAuth redirect URI
- `SERVER_ID` - Discord server ID

## Future Enhancements

### FastAPI Migration
The next phase could involve migrating from aiohttp to FastAPI for:
- Better API documentation with OpenAPI/Swagger
- Built-in request/response validation
- Better type hints and IDE support
- More modern async web framework

### Input Validation
- Add Pydantic models for request/response validation
- Better error messages and validation feedback
- Type safety improvements

### Template Utilities
- Create reusable template components
- Better template organization
- Template caching and optimization

## Testing

To test the refactored web server:

1. **Unit Tests**: Test individual modules in isolation
2. **Integration Tests**: Test the complete web server
3. **End-to-End Tests**: Test with the Discord bot

## Contributing

When adding new features to the web server:

1. **Routes**: Add to appropriate route module (`auth.py`, `pages.py`, or `api.py`)
2. **Middleware**: Add to appropriate middleware module
3. **Utilities**: Add to appropriate utility module
4. **Configuration**: Add to `config/settings.py`
5. **Documentation**: Update this README and add docstrings 