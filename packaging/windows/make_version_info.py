"""Generates the Windows VERSIONINFO resource for PyInstaller.

Usage: python packaging/windows/make_version_info.py 0.1.0 > version_info.txt
SignPath enforces the product name and version, so they must match
.signpath/artifact-configuration.xml.
"""

import re
import sys

raw = sys.argv[1] if len(sys.argv) > 1 else "0.0.0"
nums = [int(n) for n in re.findall(r"\d+", raw)[:3]]
nums += [0] * (4 - len(nums))
dotted = ".".join(str(n) for n in nums[:3])

print("""VSVersionInfo(
  ffi=FixedFileInfo(filevers=({v}), prodvers=({v}), mask=0x3f, flags=0x0, OS=0x40004,
                    fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904b0', [
      StringStruct('CompanyName', 'Autumnnus'),
      StringStruct('FileDescription', 'Paradox Rich Presence'),
      StringStruct('FileVersion', '{d}'),
      StringStruct('InternalName', 'ParadoxRichPresence'),
      StringStruct('LegalCopyright', 'MIT License'),
      StringStruct('OriginalFilename', 'ParadoxRichPresence.exe'),
      StringStruct('ProductName', 'Paradox Rich Presence'),
      StringStruct('ProductVersion', '{d}')])]),
    VarFileInfo([VarStruct('Translation', [0x0409, 1200])])
  ]
)""".format(v=", ".join(str(n) for n in nums), d=dotted))
