"""Prevent loss of the early GPU gate operation when rebuilding the eMMC SPL."""
import struct
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class EmmcGpuSpl(unittest.TestCase):
    def test_signed_firmware_contains_early_gpu_enable_and_barrier(self):
        toc = (ROOT / 'boards/t95h/boot/emmc/spl-reset-fifo.toc0').read_bytes()
        self.assertEqual(toc[:8], b'TOC0.GLH')
        firmware = []
        for i in range(struct.unpack_from('<I', toc, 24)[0]):
            name, offset, size, _, _, load = struct.unpack_from('<6I', toc, 48 + i * 32)
            if name == 0x10202:
                self.assertEqual(load, 0x20060)
                self.assertLessEqual(offset + size, len(toc))
                firmware.append(toc[offset:offset + size])
        self.assertEqual(len(firmware), 1)
        # Linked clock_init_safe: x0=0x07010250; x1=x0 then post-increment
        # by192. Thus stur wzr,[x1,#-188] writes0 to0x07010254.
        # DMB precedes the write and DSB follows, before calibration resumes.
        instructions = [0xd2804a00, 0xa9bf7bfd, 0xf2a0e020, 0xaa0003e1,
                        0x910003fd, 0xb9400002, 0x321c0042, 0xb80c0422,
                        0xb940c002, 0x321f0042, 0xb900c002, 0xd5033fbf,
                        0xb814403f, 0xd5033f9f, 0xb940c001]
        sequence = struct.pack('<' + 'I' * len(instructions), *instructions)
        self.assertEqual(firmware[0].count(sequence), 1,
                         'Early GPU gate initialization missing from signed SPL')

if __name__ == '__main__':
    unittest.main()
