# Python HTTP server

A small, multithreaded **HTTP/1.1 learning project** built for the [CodeCrafters HTTP server challenge](https://codecrafters.io/challenges/http-server/overview). It implements request parsing, four GET routes, file upload, and optional gzip on echo responses using Python's standard library. It is **not a general-purpose or production-ready HTTP server**.

## Try it locally

Requires Python 3.12 or later. From the repository root:

```bash
mkdir -p served-files
python3 -m app.main --directory ./served-files
```

In a second terminal:

```bash
curl -i http://localhost:4221/
curl -i http://localhost:4221/echo/hello
curl -i http://localhost:4221/user-agent
curl -i --data-binary @README.md http://localhost:4221/files/readme.txt
curl -i http://localhost:4221/files/readme.txt
curl -i -H 'Accept-Encoding: gzip' --compressed http://localhost:4221/echo/hello
```

The default port is `4221`; optionally pass `--port NUMBER`. The configured directory must already exist. The CodeCrafters-compatible launcher, `./your_program.sh --directory ./served-files`, uses Pipenv and requires `pipenv` to be installed; direct Python execution has no third-party runtime dependencies.

## Supported behavior

| Request | Behavior |
| --- | --- |
| `GET /` | Empty `200 OK` response. |
| `GET /echo/<text>` | Echoes URL-decoded path bytes; uses gzip if the client accepts it. |
| `GET /user-agent` | Returns the request's User-Agent value, if present. |
| `GET /files/<filename>` | Returns binary file content, or `404` if missing. |
| `POST /files/<filename>` | Saves exactly the request body bytes and returns `201`. Requires `Content-Length`. |

Requests are read until the header boundary and then through the advertised `Content-Length`, even across multiple socket reads. Responses use byte-accurate `Content-Length`, and each connection handles one request before closing. File routes accept a **single filename** within `--directory`; encoded separators, `..`, and symlinks resolving outside it are rejected. The implementation limits headers to 16 KiB and bodies to 8 MiB, and returns errors for malformed framing rather than writing partial uploads.

## Architecture and evidence

- [`app/main.py`](app/main.py): socket listener and per-connection threads; request parsing, dispatch, and HTTP response serialization.
- [`tests/test_http.py`](tests/test_http.py): socket-pair tests for fragmented and binary requests, header casing, gzip, invalid framing, and file-path safety.
- [`REVIEW_NOTES.md`](REVIEW_NOTES.md): starting commit, file coverage, fixes, verification, and remaining boundaries.

Run the local regression suite:

```bash
python3 -m unittest discover -s tests -v
```

## Boundaries

Only GET and POST routes above are implemented; there is no TLS, authentication, persistent connections, chunked request decoding, directory listing, or claim of complete RFC 9112 compliance. This is a local educational server: do not expose it to the internet or use it with sensitive data. The tests are local checks, **not** a claimed CodeCrafters grading result. The project originates from a CodeCrafters exercise; the repository history, not this README, is the source for attribution of individual work. No license is asserted because no license file is present.
