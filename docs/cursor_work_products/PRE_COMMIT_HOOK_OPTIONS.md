# Pre-Commit Hook Options

## Goal
Run tests, formatting, and lint checks before each commit to prevent bad code from entering the repository.

## Options

### Option 1: Simple Git Hook (Recommended)

**Approach:** Create a basic bash script that runs `make check`

**Implementation:**
```bash
#!/bin/bash
# .git/hooks/pre-commit

# Run all checks
make check

# Exit with error if any check failed
if [ $? -ne 0 ]; then
    echo "❌ Pre-commit checks failed. Please fix the issues above."
    exit 1
fi

echo "✅ All pre-commit checks passed"
exit 0
```

**Make hook executable:**
```bash
chmod +x .git/hooks/pre-commit
```

**Pros:**
- Simple: one small bash script
- Uses existing Makefile setup
- No additional dependencies
- Fast

**Cons:**
- Not configurable via config file
- Hook not committed to repository (in `.git/hooks` which is excluded)
- Must manually set up on each clone

**To share with team:**
- Document in README
- Or create a `setup-hooks.sh` script

---

### Option 2: pre-commit Framework

**Approach:** Use the `pre-commit` Python package for a more sophisticated system

**Installation:**
```bash
uv add --dev pre-commit
# or
pip install pre-commit
```

**Configuration (`.pre-commit-config.yaml`):**
```yaml
repos:
  # Run local hooks (calls make check)
  - repo: local
    hooks:
      - id: make-check
        name: Run make check
        entry: make check
        language: system
        pass_filenames: false
        always_run: true

  # Or use individual pre-commit hooks
  - repo: https://github.com/psf/black
    rev: 24.10.0
    hooks:
      - id: black
        args: ['--line-length=100']

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.8
    hooks:
      - id: ruff
        args: ['--fix']

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.13.0
    hooks:
      - id: mypy

  - repo: local
    hooks:
      - id: pytest
        name: Run pytest
        entry: uv run pytest tests/
        language: system
        pass_filenames: false
        always_run: true
```

**Install hooks:**
```bash
pre-commit install
```

**Additional commands:**
```bash
# Run on all files (not just staged)
pre-commit run --all-files

# Skip hooks for a specific commit
git commit --no-verify

# Update hook versions
pre-commit autoupdate
```

**Pros:**
- Declarative YAML configuration
- Can auto-format files before commit
- Large repository of pre-made hooks
- Can run checks in isolated environments
- Configuration file committed to repo
- Works across platforms
- Advanced features (staged files only, per-file checks, etc.)

**Cons:**
- Adds dependency (`pre-commit` package)
- More complex setup
- Some learning curve

---

### Option 3: Git Hooks in Repository

**Approach:** Store hooks in `hooks/` directory, symlink in setup

**Structure:**
```
.hooks/
  pre-commit
.git/
  hooks/
    pre-commit -> ../../.hooks/pre-commit
```

**Setup script:**
```bash
#!/bin/bash
# setup-hooks.sh

hooks_dir=".hooks"
git_hooks_dir=".git/hooks"

if [ ! -d "$hooks_dir" ]; then
    mkdir -p "$hooks_dir"
fi

# Symlink pre-commit hook
if [ -f "$hooks_dir/pre-commit" ]; then
    ln -sf "../../$hooks_dir/pre-commit" "$git_hooks_dir/pre-commit"
    chmod +x "$hooks_dir/pre-commit"
    chmod +x "$git_hooks_dir/pre-commit"
    echo "✅ Pre-commit hook installed"
else
    echo "❌ $hooks_dir/pre-commit not found"
    exit 1
fi
```

**Pros:**
- Hooks version controlled
- Team automatically gets hooks via repo
- Still simple bash script

**Cons:**
- Requires running setup script on clone
- Still basic functionality

---

## Recommendation

**Start with Option 1 (Simple Git Hook)** because:
1. You already have `make check` that does everything
2. Simplest to implement and maintain
3. No new dependencies
4. Fast

**Consider upgrading to Option 2 (pre-commit)** if:
1. You want auto-formatting on commit
2. Team grows and needs more sophisticated workflows
3. You want platform-independent hooks
4. You want per-file checks (only lint changed files)

---

## Implementation Quick Start (Option 1)

```bash
# Create the hook
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
make check
EOF

# Make it executable
chmod +x .git/hooks/pre-commit

# Test it
git add .
git commit -m "test"  # Should run make check first
```

To share with team, add to README:
```markdown
## Development Setup

After cloning, install git hooks:
```bash
make setup-hooks
```

And add to Makefile:
```makefile
setup-hooks:
	@echo "Installing git hooks..."
	@echo '#!/bin/bash\nmake check' > .git/hooks/pre-commit
	@chmod +x .git/hooks/pre-commit
	@echo "✅ Hooks installed"
```

