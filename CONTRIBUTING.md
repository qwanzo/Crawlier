# Contributing to Crawlier

We welcome contributions! Please follow these guidelines:

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/Qwanzo/crawlier.git`
3. Create a virtual environment: `python -m venv venv`
4. Activate it: `source venv/bin/activate` (or `venv\Scripts\activate` on Windows)
5. Install dev dependencies: `pip install -e ".[dev]"`

## Development Workflow

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make changes and commit: `git commit -am "Add my feature"`
3. Run tests: `pytest`
4. Run linting: `black . && flake8 .`
5. Push: `git push origin feature/my-feature`
6. Open a pull request

## Testing

Write tests for all new features. Run with:

```bash
pytest --cov=crawlier
```

## Code Style

We use Black for formatting and flake8 for linting. Format your code:

```bash
black .
flake8 .
```

## Reporting Issues

Please include:
- Python version (`python --version`)
- Crawlier version
- Steps to reproduce
- Expected vs. actual behavior

Thank you for contributing!
