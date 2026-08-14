import pathlib
import sys
import types


def installPackagePath() -> pathlib.Path:
	addon = pathlib.Path(__file__).parents[1] / "addon"
	packagePath = addon / "globalPlugins" / "whatsappWebPlusCompanion"
	sys.path.insert(0, str(addon))
	packageName = "globalPlugins.whatsappWebPlusCompanion"
	if packageName not in sys.modules:
		package = types.ModuleType(packageName)
		package.__path__ = [str(packagePath)]
		package.__package__ = packageName
		sys.modules[packageName] = package
	return packagePath
