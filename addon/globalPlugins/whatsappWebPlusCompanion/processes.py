import json
from dataclasses import dataclass

from .models import LoaderError
from .packages import PowerShellRunner, runPowerShell
from .policy import LOOPBACK_HOST


@dataclass(frozen=True, slots=True)
class Listener:
	address: str
	port: int
	pid: int


def _reachesPackage(pid: int, parents: dict[int, int], packagePids: set[int]) -> bool:
	seen: set[int] = set()
	while pid and pid not in seen:
		if pid in packagePids:
			return True
		seen.add(pid)
		pid = parents.get(pid, 0)
	return False


def validateListener(
	port: int,
	listeners: list[Listener],
	parents: dict[int, int],
	packagePids: set[int],
) -> int:
	selected = [row for row in listeners if row.port == port]
	if not selected or any(row.address != LOOPBACK_HOST for row in selected):
		raise LoaderError("listener.exposure")
	pids = {row.pid for row in selected if _reachesPackage(row.pid, parents, packagePids)}
	if len(pids) != 1:
		raise LoaderError("listener.ancestry", f"matches={len(pids)}")
	return pids.pop()


def collectProcessTopology(
	port: int,
	runner: PowerShellRunner = runPowerShell,
) -> tuple[list[Listener], dict[int, int]]:
	script = (
		f"$listeners = Get-NetTCPConnection -State Listen -LocalPort {int(port)} -ErrorAction SilentlyContinue "
		"| Select-Object LocalAddress,LocalPort,OwningProcess; "
		"$processes = Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId; "
		"@{Listeners=@($listeners);Processes=@($processes)} | ConvertTo-Json -Compress -Depth 4"
	)
	try:
		data = json.loads(runner(script) or "{}")
	except (TypeError, ValueError) as error:
		raise LoaderError("processes.json", type(error).__name__) from error
	listeners = [
		Listener(
			str(row.get("LocalAddress", "")),
			int(row.get("LocalPort") or 0),
			int(row.get("OwningProcess") or 0),
		)
		for row in data.get("Listeners", [])
		if isinstance(row, dict)
	]
	parents = {
		int(row.get("ProcessId") or 0): int(row.get("ParentProcessId") or 0)
		for row in data.get("Processes", [])
		if isinstance(row, dict) and row.get("ProcessId")
	}
	return listeners, parents
