"""Socket-level tests: no network port or third-party dependencies required."""
import gzip
import socket
import tempfile
import threading
import unittest
from pathlib import Path
from app.main import handle_client


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def request(self, *chunks):
        server, client = socket.socketpair()
        worker = threading.Thread(target=handle_client, args=(server, self.directory))
        worker.start()
        with client:
            for chunk in chunks:
                client.sendall(chunk)
            client.shutdown(socket.SHUT_WR)
            data = b""
            while True:
                part = client.recv(4096)
                if not part:
                    break
                data += part
        worker.join(timeout=3)
        self.assertFalse(worker.is_alive(), "handler did not finish")
        head, body = data.split(b"\r\n\r\n", 1)
        headers = dict(line.split(b": ", 1) for line in head.split(b"\r\n")[1:])
        self.assertEqual(int(headers[b"Content-Length"]), len(body))
        self.assertEqual(headers[b"Connection"], b"close")
        return head.split(b"\r\n", 1)[0], headers, body

    def test_root_and_unknown(self):
        self.assertEqual(self.request(b"GET / HTTP/1.1\r\n\r\n")[0], b"HTTP/1.1 200 OK")
        self.assertEqual(self.request(b"GET /unknown HTTP/1.1\r\n\r\n")[0], b"HTTP/1.1 404 Not Found")

    def test_fragmented_body_and_binary_round_trip(self):
        body = b"hello\r\n\r\n\x00\xff" * 200
        prefix = b"POST /files/data.bin HTTP/1.1\r\nContent-Length: " + str(len(body)).encode() + b"\r\n\r\n"
        status, _, data = self.request(prefix[:19], prefix[19:], body[:80], body[80:])
        self.assertEqual(status, b"HTTP/1.1 201 Created")
        self.assertEqual(data, b"")
        self.assertEqual(self.directory.joinpath("data.bin").read_bytes(), body)
        _, headers, data = self.request(b"GET /files/data.bin HTTP/1.1\r\n\r\n")
        self.assertEqual(headers[b"Content-Type"], b"application/octet-stream")
        self.assertEqual(data, body)

    def test_user_agent_case_insensitive(self):
        _, _, body = self.request(b"GET /user-agent HTTP/1.1\r\nuSeR-aGeNt: Sample/1\r\n\r\n")
        self.assertEqual(body, b"Sample/1")

    def test_echo_and_gzip(self):
        _, _, body = self.request(b"GET /echo/hello%20world HTTP/1.1\r\n\r\n")
        self.assertEqual(body, b"hello world")
        _, headers, body = self.request(b"GET /echo/hello%20world HTTP/1.1\r\nAccept-Encoding: br, GZIP\r\n\r\n")
        self.assertEqual(headers[b"Content-Encoding"], b"gzip")
        self.assertEqual(gzip.decompress(body), b"hello world")
        _, headers, body = self.request(b"GET /echo/testing HTTP/1.1\r\nAccept-Encoding: xgzip\r\n\r\n")
        self.assertNotIn(b"Content-Encoding", headers)
        self.assertEqual(body, b"testing")
        _, headers, body = self.request(b"GET /echo/testing HTTP/1.1\r\nAccept-Encoding: gzip;q=0\r\n\r\n")
        self.assertNotIn(b"Content-Encoding", headers)
        self.assertEqual(body, b"testing")
        _, headers, body = self.request(b"GET /echo/testing HTTP/1.1\r\nAccept-Encoding: gzip;q=0.00\r\n\r\n")
        self.assertNotIn(b"Content-Encoding", headers)
        self.assertEqual(body, b"testing")

    def test_missing_file(self):
        self.assertEqual(self.request(b"GET /files/missing HTTP/1.1\r\n\r\n")[0], b"HTTP/1.1 404 Not Found")

    def test_reject_traversal_and_symlink_escape(self):
        for target in (b"../outside", b"%2e%2e", b"dir%2fsecret", b"%5csecret"):
            with self.subTest(target=target):
                status, _, _ = self.request(b"POST /files/" + target + b" HTTP/1.1\r\nContent-Length: 1\r\n\r\nx")
                self.assertEqual(status, b"HTTP/1.1 403 Forbidden")
        with tempfile.TemporaryDirectory() as outside:
            (Path(outside) / "secret").write_text("safe")
            (self.directory / "link").symlink_to(Path(outside) / "secret")
            self.assertEqual(self.request(b"GET /files/link HTTP/1.1\r\n\r\n")[0], b"HTTP/1.1 403 Forbidden")
            self.assertEqual((Path(outside) / "secret").read_text(), "safe")

    def test_invalid_framing_does_not_write(self):
        invalid = (
            b"POST /files/test HTTP/1.1\r\n\r\nx",
            b"POST /files/test HTTP/1.1\r\nContent-Length: invalid\r\n\r\nx",
            b"POST /files/test HTTP/1.1\r\nContent-Length: 4\r\n\r\nx",
            b"POST /files/test HTTP/1.1\r\nContent-Length: 1\r\nContent-Length: 1\r\n\r\nx",
        )
        expected = (411, 400, 400, 400)
        for raw, code in zip(invalid, expected):
            with self.subTest(code=code):
                status, _, _ = self.request(raw)
                self.assertTrue(status.startswith(f"HTTP/1.1 {code}".encode()), status)
                self.assertFalse((self.directory / "test").exists())

    def test_large_body_rejected_without_writing(self):
        status, _, _ = self.request(b"POST /files/test HTTP/1.1\r\nContent-Length: 9000000\r\n\r\n")
        self.assertEqual(status, b"HTTP/1.1 413 Content Too Large")
        self.assertFalse((self.directory / "test").exists())

    def test_transfer_encoding_not_supported(self):
        status, _, _ = self.request(b"POST /files/test HTTP/1.1\r\nTransfer-Encoding: chunked\r\n\r\n0\r\n\r\n")
        self.assertEqual(status, b"HTTP/1.1 501 Not Implemented")

    def test_no_process_chdir_on_concurrent_requests(self):
        import os
        original = os.getcwd()
        clients = []
        workers = []
        for name in ("one", "two", "three"):
            (self.directory / name).write_text(name)
            server, client = socket.socketpair()
            workers.append(threading.Thread(target=handle_client, args=(server, self.directory)))
            clients.append((name, client))
        for worker in workers:
            worker.start()
        for name, client in clients:
            with client:
                client.sendall(f"GET /files/{name} HTTP/1.1\r\n\r\n".encode())
                client.shutdown(socket.SHUT_WR)
                reply = b""
                while True:
                    part = client.recv(4096)
                    if not part:
                        break
                    reply += part
                self.assertEqual(reply.split(b"\r\n\r\n", 1)[1], name.encode())
        for worker in workers:
            worker.join(timeout=3)
            self.assertFalse(worker.is_alive())
        self.assertEqual(os.getcwd(), original)

    def test_unknown_method(self):
        self.assertEqual(self.request(b"DELETE / HTTP/1.1\r\n\r\n")[0], b"HTTP/1.1 405 Method Not Allowed")


if __name__ == "__main__":
    unittest.main()
