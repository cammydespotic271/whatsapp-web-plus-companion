from site_scons.site_tools.NVDATool.typings import (
	AddonInfo,
	BrailleTables,
	SymbolDictionaries,
	SpeechDictionaries,
)
from site_scons.site_tools.NVDATool.utils import _

addon_info = AddonInfo(
	addon_name="whatsappWebPlusCompanion",
	addon_summary=_("WhatsApp Web Plus Companion"),
	addon_description=_(
		"Bring fast keyboard navigation and clearer screen-reader feedback from WhatsApp Web Plus to Microsoft Store WhatsApp Stable and Beta. The Companion securely loads a bundled, verified userscript and restores the connection automatically when WhatsApp replaces its renderer.",
	),
	addon_version="2026.08.14",
	addon_changelog=_(
		"Clearer force-close dialog wording and more natural WebView2 policy guidance, with validated automatic userscript updates, safe packaged fallback, accessible close-and-continue permission diagnosis, and compatibility with NVDA 2024.1 through 2026.1.",
	),
	addon_author="Muhammad",
	addon_url="https://github.com/muhammadGagah/whatsapp-web-plus-companion",
	addon_sourceURL="https://github.com/muhammadGagah/whatsapp-web-plus-companion",
	addon_docFileName="readme.html",
	addon_minimumNVDAVersion="2024.1.0",
	addon_lastTestedNVDAVersion="2026.1.1",
	addon_updateChannel=None,
	addon_license="GPL-2.0-or-later",
	addon_licenseURL="https://www.gnu.org/licenses/old-licenses/gpl-2.0.html",
)

pythonSources = ["addon/globalPlugins/whatsappWebPlusCompanion/*.py"]
i18nSources: list[str] = pythonSources + ["buildVars.py"]
excludedFiles = ["*.pyc", "__pycache__"]
baseLanguage: str = "en"
markdownExtensions: list[str] = []
brailleTables: BrailleTables = {}
symbolDictionaries: SymbolDictionaries = {}
speechDictionaries: SpeechDictionaries = {}
