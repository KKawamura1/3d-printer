"""Smoke-test the full-mesh four-view PNG generator (requires numpy/matplotlib)."""
from pathlib import Path
import struct
import tempfile
import unittest

from stl_snapshot import render


class SnapshotRenderTests(unittest.TestCase):
    def test_tetrahedron_generates_four_view_png(self):
        triangles = [
            ((0, 0, 0), (10, 0, 0), (0, 10, 0)),
            ((0, 0, 0), (10, 0, 0), (0, 0, 10)),
            ((0, 0, 0), (0, 10, 0), (0, 0, 10)),
            ((10, 0, 0), (0, 10, 0), (0, 0, 10)),
        ]
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / 'sample.stl'
            target = Path(temp) / 'sample.preview.png'
            raw = bytearray(b' ' * 80 + struct.pack('<I', len(triangles)))
            for face in triangles:
                vertices = [axis for vertex in face for axis in vertex]
                raw += struct.pack('<12fH', 0, 0, 1, *vertices, 0)
            source.write_bytes(raw)
            render(source, target)
            with target.open('rb') as result:
                head = result.read(24)
            self.assertEqual(head[:8], b'\\x89PNG\\r\\n\\x1a\\n')
            self.assertEqual(struct.unpack('>II', head[16:24]), (1440, 1080))


if __name__ == '__main__':
    unittest.main()
