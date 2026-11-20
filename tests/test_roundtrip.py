"""Round trips on synthetic data only: nothing here depends on game files."""
import os
import tempfile
import unittest

from abmatt.brres import Brres
from abmatt.converters.convert_obj import ObjConverter
from tests.lib import AbmattTest

MTL = "newmtl m1\nKd 0.8 0.8 0.8\n"
OBJ = """mtllib t.mtl
o quad
usemtl m1
v 0 0 0
v 1 0 0
v 0 1 0
v 1 1 0
vt 0 0
vt 1 0
vt 0 1
vt 1 1
vn 0 0 1
f 1/1/1 2/2/1 3/3/1
f 2/2/1 4/4/1 3/3/1
"""


def _read(path):
    with open(path, 'rb') as f:
        return f.read()


class TestRoundTrip(AbmattTest):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.obj = os.path.join(self._dir.name, 't.obj')
        with open(os.path.join(self._dir.name, 't.mtl'), 'w') as f:
            f.write(MTL)
        with open(self.obj, 'w') as f:
            f.write(OBJ)

    def _path(self, name):
        return os.path.join(self._dir.name, name)

    def _build(self):
        converter = ObjConverter(self._path('built.brres'), self.obj).convert()
        return converter.mdl0.parent

    def test_obj_build_pack_unpack(self):
        brres = self._build()
        path = self._path('built.brres')
        self.assertTrue(brres.save(path, True))
        loaded = Brres(path, read_file=True)
        self.assertEqual(['t'], [x.name for x in loaded.models])
        mdl0 = loaded.models[0]
        built = brres.models[0]
        self.assertEqual(1, len(mdl0.objects))
        self.assertEqual(len(built.vertices), len(mdl0.vertices))
        self.assertEqual(['m1'], [x.name for x in mdl0.materials])
        self.assertEqual(built.objects[0].facepoint_count, mdl0.objects[0].facepoint_count)

    def test_unpack_pack_byte_identical(self):
        self.assertTrue(self._build().save(self._path('first.brres'), True))
        first = Brres(self._path('first.brres'), read_file=True)
        self.assertTrue(first.save(self._path('second.brres'), True))
        self.assertEqual(_read(self._path('first.brres')), _read(self._path('second.brres')))

    def test_pack_is_idempotent(self):
        self.assertTrue(self._build().save(self._path('a.brres'), True))
        a = Brres(self._path('a.brres'), read_file=True)
        a.save(self._path('b.brres'), True)
        b = Brres(self._path('b.brres'), read_file=True)
        b.save(self._path('c.brres'), True)
        self.assertEqual(_read(self._path('b.brres')), _read(self._path('c.brres')))


if __name__ == '__main__':
    unittest.main()
