import importlib
import sys
import types
import unittest
from unittest import mock

from _path import installPackagePath

installPackagePath()


class FakeNativeDialog:
	instances: list["FakeNativeDialog"] = []

	def __init__(self, parent, message: str, caption: str, style: int) -> None:
		self.parent = parent
		self.message = message
		self.caption = caption
		self.style = style
		self.labels = None
		self.destroyed = False
		self.raised = False
		self.focused = False
		self.closed = False
		self.instances.append(self)

	def SetYesNoLabels(self, yesLabel: str, noLabel: str) -> None:
		self.labels = (yesLabel, noLabel)

	def SetOKCancelLabels(self, okLabel: str, cancelLabel: str) -> None:
		self.labels = (okLabel, cancelLabel)

	def Destroy(self) -> None:
		self.destroyed = True

	def Raise(self) -> None:
		self.raised = True

	def SetFocus(self) -> None:
		self.focused = True

	def Close(self) -> None:
		self.closed = True


class DialogCompatibilityTests(unittest.TestCase):
	def setUp(self) -> None:
		FakeNativeDialog.instances.clear()

	def _loadDialogs(self, *, modern: bool, modalResult: int = 5100):
		fakeWx = types.ModuleType("wx")
		fakeWx.Window = object
		fakeWx.MessageDialog = FakeNativeDialog
		fakeWx.MessageBoxCaptionStr = "Message"
		fakeWx.EVT_WINDOW_DESTROY = object()
		fakeWx.YES_NO = 1
		fakeWx.NO_DEFAULT = 2
		fakeWx.ICON_QUESTION = 4
		fakeWx.OK = 8
		fakeWx.CENTER = 16
		fakeWx.CANCEL = 32
		fakeWx.CANCEL_DEFAULT = 64
		fakeWx.OK_DEFAULT = 128
		fakeWx.ID_OK = 5100
		fakeWx.ID_YES = 5103
		fakeWx.YES = 5103

		fakeMessage = types.ModuleType("gui.message")
		fakeMessage.displayDialogAsModal = lambda dialog: modalResult
		if modern:
			fakeMessage.MessageDialog = FakeNativeDialog
			fakeMessage.Payload = object
		fakeGui = types.ModuleType("gui")
		fakeGui.message = fakeMessage

		with mock.patch.dict(
			sys.modules,
			{"wx": fakeWx, "gui": fakeGui, "gui.message": fakeMessage},
		):
			sys.modules.pop("globalPlugins.whatsappWebPlusCompanion.dialogs", None)
			module = importlib.import_module("globalPlugins.whatsappWebPlusCompanion.dialogs")
		return module, fakeWx

	def test_modern_nvda_uses_native_message_dialog_api(self) -> None:
		module, _fakeWx = self._loadDialogs(modern=True)
		self.assertIs(module.MessageDialog, FakeNativeDialog)

	def test_legacy_confirmation_is_native_safe_and_invokes_callback(self) -> None:
		module, fakeWx = self._loadDialogs(modern=False)
		confirmed = []
		destroyed = []
		dialog = module.MessageDialog(object(), "Update?", "Companion", buttons=None)
		dialog.addNoButton(label="&Not now", defaultFocus=True, fallbackAction=True)
		dialog.addYesButton(label="&Open installer", callback=lambda payload: confirmed.append(payload))
		dialog.Bind(fakeWx.EVT_WINDOW_DESTROY, lambda event: destroyed.append(event.GetEventObject()))

		dialog.Show()

		native = FakeNativeDialog.instances[-1]
		self.assertEqual(native.labels, ("Open installer", "Not now"))
		self.assertTrue(native.style & fakeWx.CANCEL_DEFAULT)
		self.assertTrue(native.style & fakeWx.CANCEL)
		self.assertTrue(native.destroyed)
		self.assertEqual(len(confirmed), 1)
		self.assertIsInstance(confirmed[0], module.Payload)
		self.assertEqual(destroyed, [dialog])

	def test_legacy_no_result_does_not_invoke_confirmation(self) -> None:
		module, _fakeWx = self._loadDialogs(modern=False, modalResult=0)
		confirmed = []
		dialog = module.MessageDialog(object(), "Update?", "Companion", buttons=None)
		dialog.addNoButton(label="Not now", defaultFocus=True, fallbackAction=True)
		dialog.addYesButton(label="Open", callback=lambda payload: confirmed.append(payload))
		dialog.Show()
		self.assertEqual(confirmed, [])

	def test_legacy_default_focus_follows_no_button_flag(self) -> None:
		module, fakeWx = self._loadDialogs(modern=False)
		dialog = module.MessageDialog(object(), "Body", "Title", buttons=None)
		dialog.addNoButton(label="&Keep", defaultFocus=False, fallbackAction=False)
		dialog.addYesButton(label="&Go", callback=lambda payload: None)
		dialog.Show()
		native = FakeNativeDialog.instances[-1]
		self.assertTrue(native.style & fakeWx.OK_DEFAULT)
		self.assertFalse(native.style & fakeWx.CANCEL_DEFAULT)


if __name__ == "__main__":
	unittest.main()
