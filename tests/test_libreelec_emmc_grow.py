import importlib.machinery
import importlib.util
from pathlib import Path
import struct
import unittest

path = Path(__file__).resolve().parents[1] / 'boards/t95h/libreelec/hardware/grow-emmc-storage'
loader = importlib.machinery.SourceFileLoader('grow_emmc', str(path))
spec = importlib.util.spec_from_loader(loader.name, loader)
m = importlib.util.module_from_spec(spec)
loader.exec_module(m)

class GrowTests(unittest.TestCase):
    def image(self):
        b = bytearray(512)
        b[:440] = bytes(range(220)) * 2
        struct.pack_into('<I', b, 440, 0x1e950002)
        b[450] = 12
        struct.pack_into('<II', b, 454, 8192, 2097152)
        b[466] = 131
        struct.pack_into('<II', b, 470, 2105344, 1048576)
        b[510:] = b'\x55\xaa'
        return b

    def test_only_storage_length_changes(self):
        b = self.image()
        new, start, count = m.plan(b, 16000000)
        self.assertEqual(new[:474], b[:474])
        self.assertEqual(new[478:], b[478:])
        self.assertEqual(start + count, 16000000)
        self.assertEqual(m.plan(new, 16000000)[0], new)

    def test_sd_rejected(self):
        b = self.image(); struct.pack_into('<I', b, 440, 0x1e950001)
        with self.assertRaises(ValueError): m.plan(b, 16000000)

    def test_extra_partition_rejected(self):
        b = self.image(); b[482] = 131
        with self.assertRaises(ValueError): m.plan(b, 16000000)

    def test_moved_partition_rejected(self):
        b = self.image(); struct.pack_into('<I', b, 470, 2107392)
        with self.assertRaises(ValueError): m.plan(b, 16000000)

    def test_shrink_and_overflow_rejected(self):
        for size in (3000000, 2**33):
            with self.assertRaises(ValueError): m.plan(self.image(), size)

    def test_bad_signature_rejected(self):
        b = self.image(); b[511] = 0
        with self.assertRaises(ValueError): m.plan(b, 16000000)
