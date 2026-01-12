# Custom Pipelines

Place your custom production pipelines in this directory.

## Getting Started

1. Copy an example from `../examples/` as a starting point
2. Modify it for your needs
3. Upload via Admin Settings → Pipelines

## Naming Convention

Use descriptive names for your pipeline files:
- `company_content_filter.py`
- `translation_pipeline.py`
- `logging_middleware.py`
- `rate_limiter.py`

## File Safety

Files in this directory are git-ignored by default to keep your custom logic private.
If you want to version control specific pipelines, add them explicitly to git.
