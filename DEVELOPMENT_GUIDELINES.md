# Kiro-Conduit Development Guidelines

## Code Quality & Standards

### Python Code Standards

**Style Guide**: PEP 8 with Black formatter
```bash
# Format code
black src/

# Check compliance
flake8 src/
```

**Type Hints**: Use Python 3.9+ type hints for all functions
```python
def intercept_request(request: Request) -> Response:
    """
    Intercept and process API request.
    
    Args:
        request: The HTTP request object
        
    Returns:
        Modified or translated response
    """
```

**Docstring Format**: Google-style docstrings
```python
def translate_to_ollama(kiro_request: Dict) -> Dict:
    """Translate Kiro API request to Ollama format.
    
    Converts Kiro's chat completion request format to Ollama's
    compatible API format, handling model name mapping and parameter
    translation.
    
    Args:
        kiro_request: Kiro API request body as dictionary
        
    Returns:
        Ollama-compatible request dictionary
        
    Raises:
        TranslationError: If request structure is invalid
    """
```

**Logging Standards**:
```python
import logging

logger = logging.getLogger(__name__)

# Use appropriate levels
logger.DEBUG("Detailed diagnostic information")
logger.INFO("General informational message")
logger.WARNING("Warning message - something unexpected")
logger.ERROR("Error occurred - request processing failed")
```

### JavaScript/TypeScript Standards (if using Frida)

**Format with Prettier**:
```json
{
  "printWidth": 100,
  "semi": true,
  "singleQuote": true,
  "tabWidth": 2
}
```

**Comment Style**:
```javascript
// Single line comment for brief notes

/*
 * Multi-line comment for complex logic
 * explaining the approach or important context
 */
```

---

## Project Structure

### Repository Layout
```
kiro-conduit_development/
├── src/
│   ├── interceptor/          # Core traffic interception logic
│   │   ├── __init__.py
│   │   ├── base.py           # Abstract interceptor base class
│   │   ├── mitmproxy_hook.py # mitmproxy add-on
│   │   ├── local_proxy.py     # Local HTTPS proxy implementation
│   │   └── dns_spoofing.py    # DNS redirection logic
│   ├── translators/          # Request/response translators
│   │   ├── __init__.py
│   │   ├── base.py           # Abstract translator base class
│   │   ├── ollama.py         # Ollama API translator
│   │   ├── openrouter.py     # OpenRouter API translator
│   │   └── anthropic.py      # Anthropic API translator
│   ├── auth/                 # Authentication handling
│   │   ├── __init__.py
│   │   ├── kiro_handler.py   # Kiro auth token management
│   │   └── token_cache.py    # Token persistence
│   ├── config/               # Configuration management
│   │   ├── __init__.py
│   │   ├── loader.py         # Config file loading
│   │   └── defaults.py       # Default configurations
│   ├── logging_utils.py      # Centralized logging setup
│   ├── exceptions.py         # Custom exception classes
│   └── main.py               # Application entry point
├── tools/
│   ├── frida_hooks/          # Frida hooking scripts
│   │   ├── certificate_hook.js
│   │   └── request_logger.js
│   ├── electron_tools/       # Electron app manipulation
│   │   ├── extract_asar.py
│   │   ├── analyze_asar.py
│   │   └── rebuild_asar.py
│   └── mitmproxy_addon/      # mitmproxy add-on scripts
│       ├── kiro_interceptor.py
│       └── schema_analyzer.py
├── tests/
│   ├── unit/
│   │   ├── test_translators.py
│   │   ├── test_interceptor.py
│   │   └── test_auth.py
│   ├── integration/
│   │   ├── test_ollama_flow.py
│   │   ├── test_openrouter_flow.py
│   │   └── test_frida_hooking.py
│   └── conftest.py           # Pytest fixtures
├── docs/
│   ├── API_REFERENCE.md      # Discovered Kiro API reference
│   ├── SETUP_GUIDE.md        # User setup instructions
│   ├── TROUBLESHOOTING.md    # Common issues
│   └── ARCHITECTURE.md       # System design documentation
├── config/
│   ├── default_config.toml   # Default configuration template
│   └── example_setup.toml    # Example user configuration
├── logs/                     # Runtime logs directory (git-ignored)
├── .gitignore
├── requirements.txt          # Python dependencies
├── setup.py                  # Package setup
├── pytest.ini                # Pytest configuration
└── README.md                 # Project overview
```

---

## Dependency Management

### Python Dependencies

**requirements.txt**:
```
# Core dependencies
mitmproxy>=10.0.0
frida>=16.0.0
requests>=2.31.0
pydantic>=2.0.0
tomli>=2.0.0

# Development dependencies
pytest>=7.0.0
pytest-cov>=4.0.0
black>=23.0.0
flake8>=6.0.0
mypy>=1.0.0

# Optional: Specific LLM client libraries
ollama>=0.1.0
openai>=1.0.0
anthropic>=0.10.0
```

**Version Pinning Strategy**:
- For libraries we depend on directly: Use minimum version `>=`
- For libraries with breaking changes: Pin to minor version `~=x.y.0`
- For critical infrastructure: Pin exact versions until tested

**Updating Dependencies**:
```bash
# Check for outdated packages
pip list --outdated

# Update specific package safely with testing
pip install --upgrade mitmproxy
pytest  # Run tests to verify compatibility
```

---

## Git Workflow & Version Control

### Branching Strategy: Git Flow

```
main/
  ├─ Only production-ready code
  └─ Tagged with version numbers (v0.1.0, v0.2.0)

develop/
  └─ Integration branch for features

feature/
  ├─ feature/certificate-pinning-detection
  ├─ feature/ollama-translator
  └─ feature/frida-integration

hotfix/
  └─ hotfix/security-issue-auth-tokens
```

### Commit Message Format

**Standard Format**:
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Code style (formatting, missing semicolons, etc.)
- `refactor`: Code refactor without feature change
- `perf`: Performance improvement
- `test`: Test addition or modification
- `chore`: Build process, dependencies, etc.

**Examples**:
```
feat(translator): add OpenRouter API translator

Implements request/response translation for OpenRouter API backend.
Supports all OpenRouter models and handles rate limiting headers.

Closes #15

---

fix(interceptor): handle certificate pinning gracefully

Certificate pinning detection now logs helpful error messages
instead of silently failing. Users can see which domains block
interception for debugging purposes.

---

docs(setup-guide): add Frida installation instructions for Windows

Added step-by-step guide for installing Frida on Windows 11 and
configuring it to work with Kiro application.
```

### Code Review Standards

**Before Submitting PR**:
- [ ] Code passes `black` formatting
- [ ] Code passes `flake8` linting
- [ ] Type hints added for all new functions
- [ ] Unit tests written and passing
- [ ] Functions have docstrings
- [ ] No hardcoded paths or credentials
- [ ] No debug prints or commented code

**Review Checklist**:
- [ ] Code follows style guidelines
- [ ] Changes are logically sound
- [ ] Error handling is adequate
- [ ] Performance implications considered
- [ ] Documentation is updated
- [ ] Tests are comprehensive

---

## Error Handling & Logging

### Custom Exception Hierarchy

```python
class ConduitException(Exception):
    """Base exception for all kiro-conduit errors"""
    pass

class InterceptionException(ConduitException):
    """Failed to intercept request"""
    pass

class TranslationException(ConduitException):
    """Failed to translate request/response"""
    pass

class AuthenticationException(ConduitException):
    """Authentication or token management failed"""
    pass

class LLMBackendException(ConduitException):
    """Target LLM backend error"""
    pass

class ConfigurationException(ConduitException):
    """Configuration loading or validation failed"""
    pass
```

### Logging Architecture

```python
import logging
import logging.handlers

def setup_logging(log_level: str, log_file: Optional[str] = None):
    """Configure logging for the application.
    
    Args:
        log_level: One of DEBUG, INFO, WARNING, ERROR, CRITICAL
        log_file: Optional path to log file. If provided, will log to both
                 console and file
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level))
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    root_logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, 
            maxBytes=10_000_000,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        root_logger.addHandler(file_handler)
```

### Sensitive Data Handling

**Never Log**:
- API keys or authentication tokens
- User credentials
- Full request/response bodies containing sensitive data
- Personal information

**Safe Logging Patterns**:
```python
# ❌ WRONG
logger.info(f"Using API key: {openrouter_key}")

# ✅ CORRECT
logger.info(f"OpenRouter backend configured")
logger.debug(f"API key length: {len(openrouter_key)} characters")

# ❌ WRONG
logger.debug(f"Full request: {request_body}")

# ✅ CORRECT
logger.debug(f"Request to {request_body['endpoint']} with model {request_body['model']}")
```

---

## Testing Standards

### Unit Test Template

```python
import pytest
from kiro_conduit.translators.ollama import OllamaTranslator
from kiro_conduit.exceptions import TranslationException

class TestOllamaTranslator:
    """Test suite for OllamaTranslator"""
    
    @pytest.fixture
    def translator(self):
        """Create translator instance for testing"""
        return OllamaTranslator()
    
    def test_translate_simple_request(self, translator):
        """Test translation of simple chat request"""
        kiro_request = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Hello"}]
        }
        
        result = translator.translate_request(kiro_request)
        
        assert result["model"] == "neural-chat:latest"
        assert result["messages"] == kiro_request["messages"]
    
    def test_unsupported_model_raises_error(self, translator):
        """Test that unsupported models raise appropriate error"""
        kiro_request = {
            "model": "unsupported-model-xyz",
            "messages": [{"role": "user", "content": "Hello"}]
        }
        
        with pytest.raises(TranslationException):
            translator.translate_request(kiro_request)
```

### Test Coverage Standards
- Minimum 80% code coverage for production code
- 100% coverage for critical paths (auth, translation, interception)
- All error paths tested

**Run Coverage**:
```bash
pytest --cov=src --cov-report=html
```

---

## Documentation Standards

### Code Documentation
- Every function has a docstring
- Complex algorithms have inline comments explaining logic
- Configuration options documented in comments

### User Documentation
- Setup guide for different interception approaches
- Configuration reference
- Troubleshooting guide for common issues
- Example configurations for each LLM provider

### API Documentation
- Document discovered Kiro API endpoints
- Request/response examples
- Authentication flow diagrams
- Known limitations and workarounds

---

## Security Considerations

### Credential Protection
- Never hardcode API keys or tokens
- Use configuration files with restricted permissions
- Load credentials from environment variables when possible
- Clear sensitive data from memory when no longer needed

### HTTPS/TLS Handling
- Properly validate certificates in production code
- Document why certificate validation is bypassed (when necessary)
- Use standard Python libraries for TLS/SSL operations
- Keep TLS certificate handling code isolated and reviewable

### Input Validation
```python
from pydantic import BaseModel, ValidationError

class ChatRequest(BaseModel):
    """Validated chat request structure"""
    model: str
    messages: list[dict]
    temperature: float = 0.7
    
    class Config:
        # Raise error on extra fields
        extra = "forbid"

# Usage
try:
    request = ChatRequest(**user_input)
except ValidationError as e:
    logger.error(f"Invalid request: {e}")
```

---

## Performance Guidelines

### Optimization Priorities
1. **Correctness** - Always prioritize correct behavior
2. **Readability** - Prefer clear code over clever code
3. **Performance** - Optimize only when measured bottlenecks exist

### Performance Monitoring
```python
import time
from functools import wraps

def log_execution_time(func):
    """Decorator to log function execution time"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        logger.debug(f"{func.__name__} took {elapsed:.3f}s")
        return result
    return wrapper

@log_execution_time
def translate_request(request):
    # ... implementation
    pass
```

### Caching Strategy
- Cache model name mappings (unlikely to change)
- Cache authentication tokens (until refresh time)
- Don't cache full request/response pairs (too much memory)

---

## Deployment & Distribution

### Release Process
1. Update version in `setup.py`
2. Create release notes documenting changes
3. Tag commit with version: `git tag v0.1.0`
4. Build distribution: `python setup.py sdist bdist_wheel`
5. Upload to PyPI (when ready)

### Update Compatibility
- Always test with multiple Python versions (3.9, 3.10, 3.11, 3.12)
- Document any breaking changes in release notes
- Provide migration guide for users updating versions

---

## Tools & IDE Setup

### Recommended Visual Studio Code Extensions
- Python (ms-python.python)
- Pylance (ms-python.vscode-pylance)
- Black Formatter (ms-python.black-formatter)
- Flake8 (ms-python.flake8)
- Pytest (littlefoxteam.vscode-python-test-adapter)

### IDE Configuration (.vscode/settings.json)
```json
{
    "python.formatting.provider": "black",
    "python.linting.enabled": true,
    "python.linting.flakeEnabled": true,
    "[python]": {
        "editor.formatOnSave": true,
        "editor.defaultFormatter": "ms-python.black-formatter"
    },
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": [
        "tests"
    ]
}
```

---

## Review Checklist for Each Phase

Before marking a phase complete, verify:

- [ ] Code follows PEP 8 / style guidelines
- [ ] All functions have type hints and docstrings
- [ ] Unit tests written and passing
- [ ] Integration tests passing
- [ ] Code coverage > 80% for the feature
- [ ] No hardcoded secrets or paths
- [ ] Error handling comprehensive
- [ ] Documentation updated
- [ ] Git commits follow format standard
- [ ] Code review completed and approved
