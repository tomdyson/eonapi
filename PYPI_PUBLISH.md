# Publishing eonpy to PyPI

This guide explains how to publish eonpy to the Python Package Index (PyPI).

## Prerequisites

1. **PyPI Account**: Create accounts on both:
   - [Test PyPI](https://test.pypi.org/account/register/) (for testing)
   - [PyPI](https://pypi.org/account/register/) (for production)

2. **API Tokens**: Generate API tokens for authentication:
   - Go to Account Settings → API tokens
   - Create tokens for both Test PyPI and PyPI
   - Save them securely (you'll only see them once)

3. **Install build tools**:
   ```bash
   pip install --upgrade build twine
   ```

## Step-by-Step Publishing Process

### 1. Prepare the Package

Ensure all files are up to date:
- [ ] `pyproject.toml` - Version number updated
- [ ] `README.md` - Documentation is current
- [ ] `LICENSE` - License file exists
- [ ] `eonpy/__init__.py` - Version matches pyproject.toml
- [ ] Code tested and working

### 2. Update Version Number

Edit `pyproject.toml`:
```toml
version = "0.1.0"  # Update this
```

Edit `eonpy/__init__.py`:
```python
__version__ = "0.1.0"  # Must match pyproject.toml
```

### 3. Clean Previous Builds

```bash
rm -rf build/ dist/ *.egg-info
```

### 4. Build the Distribution

```bash
python -m build
```

This creates:
- `dist/eonpy-0.1.0.tar.gz` (source distribution)
- `dist/eonpy-0.1.0-py3-none-any.whl` (wheel)

### 5. Test on Test PyPI (Recommended)

Upload to Test PyPI first:
```bash
twine upload --repository testpypi dist/*
```

When prompted:
- Username: `__token__`
- Password: Your Test PyPI API token (starts with `pypi-`)

Install and test:
```bash
pip install --index-url https://test.pypi.org/simple/ eonpy
```

Test the commands:
```bash
eonpy --help
eonpy export --help
eonpy stats --help
```

### 6. Upload to PyPI (Production)

Once testing is successful:
```bash
twine upload dist/*
```

When prompted:
- Username: `__token__`
- Password: Your PyPI API token

### 7. Verify Installation

```bash
pip install eonpy
eonpy --version
```

## Using .pypirc for Easier Authentication

Create `~/.pypirc`:
```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-YOUR_PRODUCTION_TOKEN_HERE

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-YOUR_TEST_TOKEN_HERE
```

Set permissions:
```bash
chmod 600 ~/.pypirc
```

Now you can upload without entering credentials:
```bash
twine upload --repository testpypi dist/*  # Test
twine upload dist/*                          # Production
```

## Automation with GitHub Actions (Future)

Create `.github/workflows/publish.yml`:
```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'
    - name: Install dependencies
      run: |
        pip install build twine
    - name: Build package
      run: python -m build
    - name: Publish to PyPI
      env:
        TWINE_USERNAME: __token__
        TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
      run: twine upload dist/*
```

Add `PYPI_API_TOKEN` to GitHub repository secrets.

## Version Numbering

Follow [Semantic Versioning](https://semver.org/):
- **MAJOR** (1.0.0): Incompatible API changes
- **MINOR** (0.1.0): New functionality, backwards compatible
- **PATCH** (0.0.1): Bug fixes, backwards compatible

Examples:
- `0.1.0` - Initial release
- `0.1.1` - Bug fix
- `0.2.0` - New features (stats command, etc.)
- `1.0.0` - Stable release

## Checklist Before Publishing

- [ ] All tests pass
- [ ] Version number updated in both files
- [ ] README.md is up to date
- [ ] CHANGELOG.md updated (if you have one)
- [ ] Code tested with `uv run eonpy`
- [ ] Built successfully: `python -m build`
- [ ] Tested on Test PyPI
- [ ] Git committed and tagged: `git tag v0.1.0`

## Troubleshooting

### "File already exists"
You can't upload the same version twice. Bump the version number.

### "Invalid credentials"
- Ensure username is `__token__`
- Check your API token is correct and hasn't expired
- Verify you're using the right token (test vs production)

### "Package name already taken"
Choose a different package name in `pyproject.toml`.

### Build fails
```bash
# Ensure dependencies are installed
pip install --upgrade build twine setuptools wheel
```

## After Publishing

1. **Create a GitHub Release**:
   - Tag: `v0.1.0`
   - Title: `Release 0.1.0`
   - Description: List changes and improvements

2. **Announce**:
   - Update README badges
   - Share on relevant forums/communities

3. **Monitor**:
   - Check [PyPI project page](https://pypi.org/project/eonpy/)
   - Monitor for issues/feedback

## Resources

- [Python Packaging Guide](https://packaging.python.org/)
- [PyPI Help](https://pypi.org/help/)
- [Twine Documentation](https://twine.readthedocs.io/)
