# Compatibility Notes

## Dependency Requirements - Fixed for Maximum Compatibility

### Issue Encountered

Initial requirements were too strict:
```toml
requires-python = ">=3.12"
dependencies = [
    "click>=8.3.0",
    "httpx>=0.28.1",
]
```

This caused installation errors on systems with:
- Older Python versions (3.9, 3.10, 3.11)
- Older pip versions that couldn't see the latest packages

Error example:
```
ERROR: Could not find a version that satisfies the requirement click>=8.3.0
ERROR: No matching distribution found for click>=8.3.0
```

### Solution Applied

Relaxed requirements to widely-available versions:

```toml
requires-python = ">=3.9"
dependencies = [
    "click>=8.0.0",    # Down from 8.3.0 - released 2021
    "httpx>=0.23.0",   # Down from 0.28.1 - released 2022
]
```

### Why These Versions?

**Python 3.9+**
- Released October 2020
- Still widely used in production
- Supports modern type hints (`list[dict]`, `Optional`, etc.)
- Async/await fully mature
- Good balance of compatibility and features

**click 8.0.0+**
- Released May 2021
- Includes all features we use:
  - Command groups (`@click.group()`)
  - Options and arguments
  - File handling
  - Version option
- Extremely stable and widely available

**httpx 0.23.0+**
- Released June 2022
- Includes all features we use:
  - Async client (`AsyncClient`)
  - POST requests with JSON
  - Timeout handling
  - Response status checking
- Well-tested and stable

### Testing Results

✅ Successfully tested on:
- Python 3.9.6
- Old pip 21.2.4 → Upgraded to 25.3
- Clean virtual environment installation
- All commands working (`export`, `stats`, `ui`)

### Supported Python Versions

The package now officially supports:
- Python 3.9
- Python 3.10
- Python 3.11
- Python 3.12
- Python 3.13

### Best Practices for Users

**Recommended Setup:**
```bash
# Upgrade pip first (avoids most issues)
pip install --upgrade pip

# Then install eonpy
pip install eonpy
```

**If you encounter dependency issues:**
```bash
# Create fresh virtual environment
python3 -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Upgrade pip
pip install --upgrade pip

# Install eonpy
pip install eonpy
```

### Future Considerations

If we need features from newer versions:
- Document minimum versions clearly
- Test on multiple Python versions before releasing
- Consider using `pyenv` or `tox` for testing
- Set up CI/CD to test on Python 3.9, 3.10, 3.11, 3.12, 3.13

### Version Matrix

| Component | Minimum | Tested With | Recommended |
|-----------|---------|-------------|-------------|
| Python    | 3.9.0   | 3.9.6, 3.12.6 | 3.11+ |
| click     | 8.0.0   | 8.0.0, 8.1.7  | Latest |
| httpx     | 0.23.0  | 0.23.0, 0.28.1| Latest |
| pip       | 21.2.4+ | 25.3.0        | Latest |

## Code Compatibility

Our code uses modern Python features but remains compatible with 3.9+:

**✅ Compatible:**
- Type hints: `list[dict]`, `Optional[str]`, `tuple[str, str]`
- Async/await
- f-strings
- Dataclasses (if we add them in future)
- Pattern matching would require 3.10+

**Future Additions:**
If we want to use Python 3.10+ only features:
- Pattern matching (`match`/`case`)
- Union types with `|` operator
- More precise type hints

Would need to bump `requires-python = ">=3.10"` and clearly document it.
