# Contributing to ACMS

Thank you for your interest in contributing to ACMS! This document provides guidelines for contributing.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/yourusername/acms.git`
3. Create a branch: `git checkout -b feature/your-feature`
4. Make your changes
5. Run tests: `pytest tests/`
6. Commit: `git commit -m "Add your feature"`
7. Push: `git push origin feature/your-feature`
8. Open a Pull Request

## Development Setup

```bash
# Clone and setup
git clone https://github.com/yourusername/acms.git
cd acms
cp .env.example .env

# Start services
docker compose up -d

# Install Python dependencies (for development)
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests
pytest tests/ -v
```

## Code Style

- Python: Follow PEP 8, use Black for formatting
- JavaScript: Use ESLint with provided config
- Commits: Use conventional commits (feat:, fix:, docs:, etc.)

## Testing

- Write tests for new features
- Ensure existing tests pass
- Aim for >80% coverage on new code

## Pull Request Process

1. Update documentation for any new features
2. Add tests for new functionality
3. Ensure CI passes
4. Request review from maintainers

## Code of Conduct

Be respectful and inclusive. We welcome contributors of all backgrounds.

## Questions?

Open an issue or join our Discord community.
