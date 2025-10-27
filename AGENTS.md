## Dependencies         
- Python 3.12 required 
- Manage dependencies via uv and virtual environments
- Use Typer for CLI parsing

## Development and agent interactions
- Encourage test-driven development: ask user to design and verify tests early on
- Implement robust error handling and logging, including context capture
- Ensure a clear project structure with separate directories for source code (src), tests (tests), documentation (docs), and configuration (config)

## Testing
- Core functions should have unit tests
- Use pytest for testing
- Maintain test coverage

## Code Style                
- Use black for formatting (line length 100) 
- Use ruff for linting
- Use mypy --strict for type checking
- All functions must have type hints and docstrings
                                                                                        
## Quality Checks
- Run make check before commits
- Ensure all linting passes
- Ensure all type checks pass
- Ensure all tests pass
