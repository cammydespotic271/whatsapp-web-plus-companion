import ctypes
from ctypes import wintypes
from dataclasses import dataclass

from .models import LoaderError


@dataclass(frozen=True, slots=True)
class SecurityProbe:
	canWrite: bool
	secureDesktop: bool
	locked: bool
	elevated: bool


def checkPreflight(probe: SecurityProbe) -> None:
	checks = (
		(not probe.canWrite, "security.noWrite"),
		(probe.secureDesktop, "security.secureDesktop"),
		(probe.locked, "security.locked"),
		(probe.elevated, "security.elevated"),
	)
	for failed, code in checks:
		if failed:
			raise LoaderError(code)


def _inputDesktopName() -> str | None:
	user32 = ctypes.WinDLL("user32", use_last_error=True)
	openInputDesktop = user32.OpenInputDesktop
	openInputDesktop.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
	openInputDesktop.restype = wintypes.HANDLE
	closeDesktop = user32.CloseDesktop
	closeDesktop.argtypes = (wintypes.HANDLE,)
	closeDesktop.restype = wintypes.BOOL
	getUserObjectInformation = user32.GetUserObjectInformationW
	getUserObjectInformation.argtypes = (
		wintypes.HANDLE,
		ctypes.c_int,
		wintypes.LPVOID,
		wintypes.DWORD,
		ctypes.POINTER(wintypes.DWORD),
	)
	getUserObjectInformation.restype = wintypes.BOOL
	desktop = openInputDesktop(0, False, 0x0001)
	if not desktop:
		return None
	try:
		needed = wintypes.DWORD()
		getUserObjectInformation(desktop, 2, None, 0, ctypes.byref(needed))
		if not needed.value:
			return None
		buffer = ctypes.create_unicode_buffer(needed.value // ctypes.sizeof(ctypes.c_wchar))
		if not getUserObjectInformation(desktop, 2, buffer, needed.value, ctypes.byref(needed)):
			return None
		return buffer.value
	finally:
		closeDesktop(desktop)


def _isElevated() -> bool:
	kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
	advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
	kernel32.GetCurrentProcess.argtypes = ()
	kernel32.GetCurrentProcess.restype = wintypes.HANDLE
	kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
	kernel32.CloseHandle.restype = wintypes.BOOL
	advapi32.OpenProcessToken.argtypes = (
		wintypes.HANDLE,
		wintypes.DWORD,
		ctypes.POINTER(wintypes.HANDLE),
	)
	advapi32.OpenProcessToken.restype = wintypes.BOOL
	advapi32.GetTokenInformation.argtypes = (
		wintypes.HANDLE,
		ctypes.c_int,
		wintypes.LPVOID,
		wintypes.DWORD,
		ctypes.POINTER(wintypes.DWORD),
	)
	advapi32.GetTokenInformation.restype = wintypes.BOOL
	token = wintypes.HANDLE()
	if not advapi32.OpenProcessToken(kernel32.GetCurrentProcess(), 0x0008, ctypes.byref(token)):
		raise LoaderError("security.probe", "openToken")
	try:
		elevation = wintypes.DWORD()
		returned = wintypes.DWORD()
		if not advapi32.GetTokenInformation(
			token,
			20,
			ctypes.byref(elevation),
			ctypes.sizeof(elevation),
			ctypes.byref(returned),
		):
			raise LoaderError("security.probe", "tokenElevation")
		return bool(elevation.value)
	finally:
		kernel32.CloseHandle(token)


def buildSecurityProbe() -> SecurityProbe:
	import NVDAState

	desktopName = _inputDesktopName()
	return SecurityProbe(
		canWrite=bool(NVDAState.shouldWriteToDisk()),
		secureDesktop=desktopName is None,
		locked=desktopName is not None and desktopName.casefold() != "default",
		elevated=_isElevated(),
	)
