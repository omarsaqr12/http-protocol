"""A small, deliberately single-request-per-connection HTTP/1.1 learning server."""

import argparse
import gzip
import socket
import threading
from pathlib import Path
from urllib.parse import unquote_to_bytes

HOST = "localhost"
PORT = 4221
MAX_HEADERS = 16 * 1024
MAX_BODY = 8 * 1024 * 1024
REASONS = {
    200: "OK", 201: "Created", 400: "Bad Request", 403: "Forbidden",
    404: "Not Found", 405: "Method Not Allowed", 411: "Length Required",
    413: "Content Too Large", 500: "Internal Server Error",
    501: "Not Implemented",
}


class HTTPError(Exception):
    def __init__(self, status):
        self.status = status


def read_request(connection):
    """Read HTTP headers and exactly the advertised number of body octets."""
    connection.settimeout(5)
    data = b""
    while b"\r\n\r\n" not in data:
        part = connection.recv(4096)
        if not part:
            raise HTTPError(400)
        data += part
        if len(data.split(b"\r\n\r\n", 1)[0]) > MAX_HEADERS:
            raise HTTPError(413)
    head, initial_body = data.split(b"\r\n\r\n", 1)
    try:
        lines = head.decode("iso-8859-1").split("\r\n")
        method, target, version = lines[0].split(" ")
        if version not in ("HTTP/1.0", "HTTP/1.1") or not target.startswith("/"):
            raise ValueError("invalid start line")
        headers = {}
        for line in lines[1:]:
            name, separator, value = line.partition(":")
            if not separator or not name or name.strip() != name or not name.isascii() or not all(c.isalnum() or c == "-" for c in name):
                raise ValueError("invalid header")
            key = name.lower()
            if key in headers:
                raise ValueError("duplicate header")
            headers[key] = value.strip()
        if "transfer-encoding" in headers:
            raise HTTPError(501)
        length_text = headers.get("content-length")
        if length_text is None:
            if method == "POST":
                raise HTTPError(411)
            length = 0
        elif not length_text.isascii() or not length_text.isdecimal():
            raise ValueError("invalid content length")
        else:
            length = int(length_text)
        if length > MAX_BODY:
            raise HTTPError(413)
    except ValueError as error:
        raise HTTPError(400) from error
    body = initial_body[:length]
    while len(body) < length:
        part = connection.recv(min(4096, length - len(body)))
        if not part:
            raise HTTPError(400)
        body += part
    return method, target, headers, body


def file_path(directory, raw_name):
    """Keep file routes to a single file inside the configured directory."""
    try:
        name = unquote_to_bytes(raw_name).decode("utf-8")
    except UnicodeError as error:
        raise HTTPError(400) from error
    if name in ("", ".", "..") or "/" in name or "\\" in name or "\x00" in name:
        raise HTTPError(403)
    root = directory.resolve()
    candidate = (root / name).resolve()
    if candidate.parent != root:
        raise HTTPError(403)
    return candidate


def dispatch(method, target, headers, body, directory):
    """Return (status, response bytes, additional response headers)."""
    path = target.split("?", 1)[0]
    if method not in ("GET", "POST"):
        raise HTTPError(405)
    if path.startswith("/files/"):
        path_on_disk = file_path(directory, path[len("/files/"):])
        if method == "POST":
            try:
                path_on_disk.write_bytes(body)
            except PermissionError as error:
                raise HTTPError(403) from error
            except OSError as error:
                raise HTTPError(500) from error
            return 201, b"", {}
        try:
            return 200, path_on_disk.read_bytes(), {"Content-Type": "application/octet-stream"}
        except FileNotFoundError as error:
            raise HTTPError(404) from error
        except IsADirectoryError as error:
            raise HTTPError(403) from error
        except PermissionError as error:
            raise HTTPError(403) from error
        except OSError as error:
            raise HTTPError(500) from error
    if method != "GET":
        raise HTTPError(404)
    if path == "/":
        return 200, b"", {}
    if path == "/user-agent":
        return 200, headers.get("user-agent", "").encode("iso-8859-1"), {"Content-Type": "text/plain"}
    if path.startswith("/echo/"):
        content = unquote_to_bytes(path[len("/echo/"):])
        extra = {"Content-Type": "text/plain"}
        encodings = headers.get("accept-encoding", "").split(",")
        accepts_gzip = False
        for encoding in encodings:
            name, *parameters = encoding.split(";")
            if name.strip().lower() == "gzip":
                accepts_gzip = not any(
                    parameter.strip().lower().replace(" ", "") == "q=0"
                    or parameter.strip().lower().replace(" ", "") == "q=0.0"
                    for parameter in parameters
                )
        if accepts_gzip:
            content = gzip.compress(content)
            extra["Content-Encoding"] = "gzip"
        return 200, content, extra
    raise HTTPError(404)


def response_bytes(status, body=b"", extra=None):
    extra = extra or {}
    lines = [f"HTTP/1.1 {status} {REASONS[status]}", f"Content-Length: {len(body)}", "Connection: close"]
    lines.extend(f"{name}: {value}" for name, value in extra.items())
    return ("\r\n".join(lines) + "\r\n\r\n").encode("ascii") + body


def handle_client(connection, directory):
    with connection:
        try:
            method, target, headers, body = read_request(connection)
            status, content, extra = dispatch(method, target, headers, body, directory)
            reply = response_bytes(status, content, extra)
        except HTTPError as error:
            reply = response_bytes(error.status)
        except (socket.timeout, ConnectionError, OSError):
            reply = response_bytes(400)
        try:
            connection.sendall(reply)
        except OSError:
            pass


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path.cwd(), help="directory for /files routes")
    parser.add_argument("--port", type=int, default=PORT, help="local listening port (default: 4221)")
    args = parser.parse_args(argv)
    if not args.directory.is_dir():
        parser.error("--directory must be an existing directory")
    with socket.create_server((HOST, args.port)) as server:
        server.listen()
        while True:
            connection, _ = server.accept()
            threading.Thread(target=handle_client, args=(connection, args.directory), daemon=True).start()


if __name__ == "__main__":
    main()
