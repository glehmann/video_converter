# Validation Instructions

This project uses the following tools to ensure code quality and correctness:

## 1. Code Formatting
Format the code using `ruff`:
```bash
uv run ruff format .
```

## 2. Linting
Lint the code and automatically fix issues where possible using `ruff`:
```bash
uv run ruff check . --fix
```

## 3. Type Checking
Check static types using `ty`:
```bash
uv run ty check
```

## 4. Testing
Run the unit tests using `pytest`:
```bash
uv run pytest
```

Ensure all commands pass before committing changes.
