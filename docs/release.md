# Release Checklist

## Before GitHub

- Confirm `.gitignore` excludes secrets and local state
- Ensure `wrangler.toml` has no secrets
- Update `HASH_SALT` via `wrangler secret put HASH_SALT`
- Verify `README.md` and `cloudflare/README.md`
- Run tests (optional): `pytest`

## Before PyPI

1. Bump version in `pyproject.toml` and `trainwatch/__init__.py`.
2. Build package:

```
python -m build
```

3. Upload to PyPI:

```
python -m twine upload dist/*
```

## Recommended tags

- Create a Git tag: `v0.1.0`
- Push tags to GitHub
