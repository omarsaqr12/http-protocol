# Engineering review / handoff — HTTP server

## Identity and baseline

- Repository: `omarsaqr12/http-protocol`, default branch `main`.
- Baseline commit: `346b960537b73ffa5fa1a40446023006ef89554b` (inspected through the connected GitHub API; default branch not edited).
- Category: CodeCrafters HTTP server challenge; educational Python socket application.
- Evidence standard: inspect all tracked files and exercise real socket behavior, malformed requests, binary/fragmented bodies, and directory boundaries. RFC 9112's request framing and content length rules provide protocol context; this implementation is not a complete RFC implementation.

## Baseline inventory and file coverage

All **six** tracked files were read in full: `Pipfile`, `Pipfile.lock`, `README.md`, `app/main.py`, `codecrafters.yml`, and `your_program.sh`. No tracked binary/vendor material or results were present. The CodeCrafters scaffold/configuration is retained without changes. Its launcher is tracked without an executable bit; invoke it with `sh your_program.sh` after installing Pipenv. No external tests, grader scores, or contribution breakdown were available.

## Confirmed baseline problems (source review)

1. **Unsafe shared state:** per-client threads call `os.chdir` for file routes, changing every thread's process-wide current directory.
2. **Incorrect framing / data loss:** a single `recv(1024)` is used for the entire HTTP request; POST takes only the last CRLF-separated string as its body, without honoring `Content-Length`.
3. **Byte-count bugs:** text files are read/written with implicit text encoding; response lengths are computed from Python character counts, not necessarily wire bytes; some bodies contain an extra CRLF after the advertised length.
4. **Incorrect routing and compression:** routing searches the entire request for `files`/`user-agent` rather than matching the request target; gzip token detection and response assembly are ad hoc.
5. **Reproducibility / claims:** README uses placeholder Git URLs, an incorrect `main.py` run path/argument form, malformed code fences, and asserts an MIT license although no LICENSE is tracked. There were no automated tests.

## Changes and verification

- Implemented bounded header/body parsing, byte-safe file I/O and responses, correct route dispatch and case-insensitive headers.
- Disallowed file traversal and symlink escape; removed process-wide `chdir`; implemented gzip response negotiation for the echo route.
- Added socketpair regression tests and a standard-library quickstart; kept the original CodeCrafters files intact.
- Added lightweight GitHub Actions test workflow (Python 3.12); check the PR for the actual remote CI outcome.

Local verification: `python3 -m unittest discover -s tests -v`; `python3 -m py_compile app/main.py tests/test_http.py`. The tests cover file uploads split across recv calls, binary bodies, accurate response framing, malformed lengths, oversized inputs, concurrent file requests, traversal and symlink rejection, and supported routes. This is a local test suite, not an independently reproduced CodeCrafters score.

## Deliberate scope and limitations

The server closes after each response, has no chunked request parsing, no TLS, no authentication, no request streaming to disk, and no claim of general HTTP/1.1 compliance. There is no adversarial filesystem race hardening against another local process that changes files or symlinks during a request. It is intended for local exercise use. The original CodeCrafters grader, Pipenv launcher, and Python 3.12 runtime may be unavailable locally; their results must be reported separately from the local tests. No feature expansion or license change was undertaken.
