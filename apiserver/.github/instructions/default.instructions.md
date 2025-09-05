---
applyTo: '**/*.py'
---

## Style Guide

- The max characters per line is 119.

## Testing Guidelines

- The project uses pytest for testing.
- Ensure the test file style follows pytest conventions and best practices.
- Apply `--reuse-db -s --maxfail=1` flags when running pytest by default.
- When a domain name is needed for constructing test cases, prefer "example.com".
