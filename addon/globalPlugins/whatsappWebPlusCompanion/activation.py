import os
import socket
import time
from collections.abc import Callable
from threading import Event

from .models import LoaderError
from .policy import ENDPOINT_DEADLINE, LOOPBACK_HOST, ChannelPolicy


def reserveLoopbackPort() -> int:
	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
		sock.bind((LOOPBACK_HOST, 0))
		port = int(sock.getsockname()[1])
	if port < 1024:
		raise LoaderError("activation.lowPort")
	return port


def shellActivate(target: str) -> None:
	os.startfile(target)


def activateAumid(policy: ChannelPolicy, activate: Callable[[str], None] = shellActivate) -> None:
	try:
		activate(f"shell:AppsFolder\\{policy.aumid}")
	except OSError as error:
		raise LoaderError("activation.failed", type(error).__name__) from error


def waitForEndpoint(
	port: int,
	probe: Callable[[int], bool],
	cancelEvent: Event,
	deadline: float = ENDPOINT_DEADLINE,
) -> None:
	end = time.monotonic() + deadline
	started = time.monotonic()
	while time.monotonic() < end:
		if cancelEvent.is_set():
			raise LoaderError("operation.cancelled")
		if probe(port):
			return
		elapsed = time.monotonic() - started
		interval = 0.2 if elapsed < 5.0 else 0.5
		if cancelEvent.wait(min(interval, max(0.0, end - time.monotonic()))):
			raise LoaderError("operation.cancelled")
	raise LoaderError("endpoint.timeout")
