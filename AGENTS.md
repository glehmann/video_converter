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

## Jujutsu (jj) Commands

This project uses `jj` (Jujutsu) for version control. Here are some common commands:

*   **Check status**: `jj status`
*   **Show differences**: `jj diff`
*   **Create a new commit**: `jj commit -m "Your commit message"`
*   **Create a new empty commit**: `jj new`
*   **Describe a commit**: `jj describe -m "Your commit message"`
*   **View commit history**: `jj log`
*   **Undo last operation**: `jj undo`
