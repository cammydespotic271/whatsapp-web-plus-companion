from collections.abc import Callable

from .models import Channel, LoaderError, OperationResult
from .packages import PackageInfo, PackageProcessCloseResult, findPackage, forceClosePackageProcesses
from .policy import CHANNELS, ChannelPolicy
from .security import SecurityProbe, buildSecurityProbe, checkPreflight

PackageFinder = Callable[[ChannelPolicy], PackageInfo | None]
ProcessCloser = Callable[[PackageInfo], PackageProcessCloseResult]
ProbeBuilder = Callable[[], SecurityProbe]


def forceCloseOperation(
	packageFinder: PackageFinder = findPackage,
	processCloser: ProcessCloser = forceClosePackageProcesses,
	probeBuilder: ProbeBuilder = buildSecurityProbe,
) -> OperationResult:
	checkPreflight(probeBuilder())
	closedCount = 0
	foundCount = 0
	remainingChannels: list[str] = []
	errors: list[str] = []
	for channel in (Channel.STABLE, Channel.BETA):
		try:
			package = packageFinder(CHANNELS[channel])
		except LoaderError as error:
			errors.append(error.code)
			remainingChannels.append(channel.value)
			continue
		if package is None:
			continue
		try:
			result = processCloser(package)
		except LoaderError as error:
			errors.append(error.code)
			remainingChannels.append(channel.value)
			continue
		foundCount += result.foundCount
		closedCount += result.closedCount
		if result.remainingCount:
			remainingChannels.append(channel.value)

	values = {
		"closedCount": closedCount,
		"foundCount": foundCount,
		"remainingChannels": tuple(remainingChannels),
	}
	if not foundCount and not errors:
		return OperationResult(True, "processes.none", "processes.none", values)
	if foundCount and closedCount == foundCount and not errors:
		return OperationResult(True, "processes.closed", "processes.closed", values)
	if closedCount:
		return OperationResult(False, "processes.partial", "processes.partial", values)
	return OperationResult(False, "processes.failed", "processes.failed", values)
