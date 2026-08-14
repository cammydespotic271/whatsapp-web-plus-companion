import unittest

from _path import installPackagePath

installPackagePath()

from globalPlugins.whatsappWebPlusCompanion.models import Channel, LoaderError, OperationState
from globalPlugins.whatsappWebPlusCompanion.policy import CHANNELS, EXPECTED_ORIGIN
from globalPlugins.whatsappWebPlusCompanion.security import SecurityProbe, checkPreflight


class PolicySecurityTests(unittest.TestCase):
	def test_channels_are_exact_and_immutable(self) -> None:
		self.assertEqual(CHANNELS[Channel.STABLE].aumid, "5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App")
		self.assertEqual(
			CHANNELS[Channel.BETA].packageFamily,
			"5319275A.51895FA4EA97F_cv1g1gvanyjgm",
		)
		self.assertEqual(EXPECTED_ORIGIN, "https://web.whatsapp.com")
		with self.assertRaises(TypeError):
			CHANNELS[Channel.STABLE] = CHANNELS[Channel.BETA]
		self.assertEqual(OperationState.IDLE.value, "idle")

	def test_each_unsafe_context_is_rejected(self) -> None:
		for field, code in (
			("canWrite", "security.noWrite"),
			("secureDesktop", "security.secureDesktop"),
			("locked", "security.locked"),
			("elevated", "security.elevated"),
		):
			values = dict(canWrite=True, secureDesktop=False, locked=False, elevated=False)
			values[field] = field != "canWrite"
			with self.subTest(field=field), self.assertRaisesRegex(LoaderError, code):
				checkPreflight(SecurityProbe(**values))

	def test_safe_context_passes(self) -> None:
		checkPreflight(SecurityProbe(True, False, False, False))
