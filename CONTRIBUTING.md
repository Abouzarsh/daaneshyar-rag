# Contributing

Thanks for taking the time to improve Daaneshyar.

## Before opening a pull request

1. Open an issue for behavior changes that affect storage or public APIs.
2. Keep the local-first default and Persian text behavior intact.
3. Add or update tests for retrieval and ingestion changes.
4. Do not commit real customer documents, model weights, secrets, or .env.

## Development checks

    cd backend
    ruff check .
    pytest --cov=app

    cd ../frontend
    npm run lint
    npm run build

## Commit style

Use short, descriptive commits. Conventional prefixes are helpful but not
mandatory:

- feat: user-visible behavior
- fix: a bug correction
- test: test-only changes
- docs: documentation
- chore: tooling or maintenance

## Pull request notes

Explain the problem, the chosen tradeoff, how you tested it, and whether a data
migration or re-index is required. Screenshots are useful for visual changes.
