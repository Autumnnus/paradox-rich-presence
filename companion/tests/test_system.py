import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from paradox_rich_presence import system  # noqa: E402


class SystemTests(unittest.TestCase):
    def test_process_list_contains_python(self):
        names = system.running_process_names()
        self.assertTrue(any("python" in n for n in names), names)

    def test_documents_dir(self):
        self.assertTrue(system.documents_dir().is_absolute())

    def test_data_dir_is_created(self):
        self.assertTrue(system.data_dir().is_dir())


@unittest.skipUnless(system.IS_WINDOWS, "Windows only")
class WindowsTests(unittest.TestCase):
    def test_known_documents_folder_exists(self):
        self.assertTrue(system.documents_dir().is_dir())

    def test_single_instance_and_stop_signal(self):
        first = system.WindowsInstance()
        second = system.WindowsInstance()
        self.assertTrue(second.already_running)
        self.assertFalse(first.stop_requested())
        second.request_stop()
        self.assertTrue(first.stop_requested())


if __name__ == "__main__":
    unittest.main()
