# Sappho
Improves your writing

http://sappho.pythonanywhere.com/

## Request limit

Request bodies are limited to 500,000 bytes by default, before form parsing or
analysis. The limit includes URL-encoded field names and escaping. An optional
`MAX_CONTENT_LENGTH` environment variable sets a positive integer limit in bytes;
invalid or nonpositive values fail at startup rather than disabling the limit.

## Route regression tests

Use a fresh temporary environment made with a system Python, not the committed
`venv`. The route tests replace text analysis and environment settings with mocks;
they perform no corpus downloads, database access, or external service calls.

```sh
python3 -I -m venv /tmp/sappho-request-tests
/tmp/sappho-request-tests/bin/python -I -m pip --isolated install --index-url https://pypi.org/simple --only-binary=:all: Flask==3.1.3 Werkzeug==3.1.9
/tmp/sappho-request-tests/bin/python -I -B -m unittest discover -s tests -v
```
