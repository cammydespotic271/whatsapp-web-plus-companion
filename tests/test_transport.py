import base64
import hashlib
import io
import json
import socket
import threading
import unittest
from unittest.mock import patch

from _path import installPackagePath

installPackagePath()

from globalPlugins.whatsappWebPlusCompanion.http import httpGetJson
from globalPlugins.whatsappWebPlusCompanion.models import LoaderError
from globalPlugins.whatsappWebPlusCompanion.websocket import WebSocket, encodeClientFrame, readServerFrame


_WEBSOCKET_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


def serve(response: bytes, holdOpen: threading.Event | None = None) -> int:
	server = socket.socket()
	server.bind(("127.0.0.1", 0))
	server.listen(1)
	port = server.getsockname()[1]

	def worker() -> None:
		with server:
			client, _ = server.accept()
			with client:
				client.recv(4096)
				client.sendall(response)
				if holdOpen is not None:
					holdOpen.wait(1.0)

	threading.Thread(target=worker, daemon=True).start()
	return port


def serveWebSocketHandshake(status: str) -> int:
	server = socket.socket()
	server.bind(("127.0.0.1", 0))
	server.listen(1)
	port = server.getsockname()[1]

	def worker() -> None:
		with server:
			client, _ = server.accept()
			with client:
				request = bytearray()
				while b"\r\n\r\n" not in request:
					request.extend(client.recv(4096))
				headers = {}
				for line in bytes(request).decode("ascii").split("\r\n")[1:]:
					if not line:
						break
					name, value = line.split(":", 1)
					headers[name.lower()] = value.strip()
				key = headers["sec-websocket-key"]
				accept = base64.b64encode(hashlib.sha1((key + _WEBSOCKET_GUID).encode("ascii")).digest())
				response = (
					status.encode("ascii")
					+ b"\r\nUpgrade: WebSocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: "
					+ accept
					+ b"\r\n\r\n"
				)
				client.sendall(response)

	threading.Thread(target=worker, daemon=True).start()
	return port


class TransportTests(unittest.TestCase):
	def test_websocket_accepts_valid_101_reason_phrases(self) -> None:
		for status in (
			"HTTP/1.1 101 Switching Protocols",
			"HTTP/1.1 101 WebSocket Protocol Handshake",
		):
			with self.subTest(status=status):
				port = serveWebSocketHandshake(status)
				webSocket = WebSocket.connect(f"ws://127.0.0.1:{port}/devtools/page/test", 1.0)
				webSocket.close()

	def test_websocket_rejects_non_101_status(self) -> None:
		port = serveWebSocketHandshake("HTTP/1.1 200 OK")
		with self.assertRaisesRegex(LoaderError, "websocket.handshake"):
			WebSocket.connect(f"ws://127.0.0.1:{port}/devtools/page/test", 1.0)

	def test_exact_bounded_json_response(self) -> None:
		body = json.dumps({"Protocol-Version": "1.3"}).encode()
		response = (
			b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: "
			+ str(len(body)).encode()
			+ b"\r\nConnection: close\r\n\r\n"
			+ body
		)
		self.assertEqual(httpGetJson(serve(response), "/json/version"), {"Protocol-Version": "1.3"})

	def test_content_length_response_does_not_wait_for_connection_close(self) -> None:
		body = json.dumps({"Browser": "Edg/151.0.4129.72"}).encode()
		response = (
			b"HTTP/1.1 200 OK\r\nContent-Type:application/json; charset=UTF-8\r\nContent-Length:"
			+ str(len(body)).encode()
			+ b"\r\n\r\n"
			+ body
		)
		holdOpen = threading.Event()
		try:
			self.assertEqual(
				httpGetJson(serve(response, holdOpen), "/json/version", timeout=0.1),
				{"Browser": "Edg/151.0.4129.72"},
			)
		finally:
			holdOpen.set()

	def test_redirect_and_chunking_are_rejected(self) -> None:
		for response in (
			b"HTTP/1.1 302 Found\r\nLocation: http://example.com\r\nContent-Length: 0\r\n\r\n",
			b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n0\r\n\r\n",
		):
			with self.assertRaises(LoaderError):
				httpGetJson(serve(response), "/json/list")

	@patch(
		"globalPlugins.whatsappWebPlusCompanion.websocket.os.urandom",
		return_value=b"\x01\x02\x03\x04",
	)
	def test_large_client_frames_are_masked(self, _randomBytes) -> None:
		payload = b"x" * 300_000
		frame = encodeClientFrame(1, payload)
		self.assertEqual(frame[1] & 0x7F, 127)
		length = int.from_bytes(frame[2:10], "big")
		self.assertEqual(length, len(payload))
		mask = frame[10:14]
		unmasked = bytes(value ^ mask[index % 4] for index, value in enumerate(frame[14:]))
		self.assertEqual(unmasked, payload)

	def test_masked_server_frame_is_rejected(self) -> None:
		with self.assertRaisesRegex(LoaderError, "websocket.protocol"):
			readServerFrame(io.BytesIO(b"\x81\x80"))
