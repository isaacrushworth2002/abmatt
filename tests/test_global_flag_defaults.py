import struct
import unittest
from unittest import mock

import numpy as np

from abmatt.brres.lib import decoder
from abmatt.brres.lib.unpacking.unpack_mdl0 import unpack_material
from abmatt.brres.mdl0.material.layer import Layer
from abmatt.brres.tex0 import Tex0
from abmatt.converters.convert_obj import VertexColorImporter
from abmatt.converters.geometry import Geometry


def draw(cmd, indices):
    return struct.pack('>BH', cmd, len(indices)) + b''.join(struct.pack('>H', i) for i in indices)


class FakePolygon:
    name = 'p'

    def __init__(self, data, count):
        self.data = data
        self.facepoint_count = count


class TestLayerDefaults(unittest.TestCase):
    def test_unknown_refs_are_kept(self):
        self.assertFalse(Layer.RENAME_UNKNOWN_REFS)
        self.assertFalse(Layer.REMOVE_UNKNOWN_REFS)


class TestDecodeIndices(unittest.TestCase):
    def decode(self, data, count):
        return decoder.decode_indices(FakePolygon(data, count), '>H')[0]

    def test_quads_become_two_triangles(self):
        tris = self.decode(draw(0x80, [0, 1, 2, 3]), 4)
        self.assertEqual([[(0,), (1,), (2,)], [(0,), (2,), (3,)]], [[tuple(p) for p in t] for t in tris])

    def test_fan_becomes_triangles_around_first_point(self):
        tris = self.decode(draw(0xa0, [5, 6, 7, 8]), 4)
        self.assertEqual([[(5,), (6,), (7,)], [(5,), (7,), (8,)]], [[tuple(p) for p in t] for t in tris])

    def test_lines_are_skipped(self):
        data = draw(0xa8, [0, 1, 2, 3]) + draw(0x90, [0, 1, 2])
        tris = self.decode(data, 7)
        self.assertEqual(1, len(tris))

    def test_matrix_loads_are_kept_and_lines_dropped(self):
        load = bytes([0x20, 0, 1, 0xb0, 0])
        data = load + draw(0xa8, [1, 2]) + draw(0x90, [3, 4, 5])
        tris, weights = decoder.decode_indices(FakePolygon(data, 5), '>H')
        self.assertEqual([[(3,), (4,), (5,)]], [[tuple(p) for p in t] for t in tris])
        self.assertEqual({0: [1]}, weights)

    def test_strips_decode_as_before(self):
        tris = self.decode(draw(0x98, [1, 2, 3, 4]), 4)
        self.assertEqual([[(1,), (2,), (3,)], [(3,), (2,), (4,)]], [[tuple(p) for p in t] for t in tris])


class TestEncodeVertexColors(unittest.TestCase):
    PRIVATE = ('encode_influences', 'encode_tex_matrices', 'encode_vertices', 'encode_normals', 'encode_colors',
               'encode_texcoords', 'construct_tris')

    def encode(self, **kwargs):
        geo = Geometry('g', 'm', None, colors=object())
        polygon = mock.MagicMock()
        mdl = polygon.parent
        with mock.patch.multiple(geo, **{f'_Geometry__{n}': mock.Mock(return_value=False) for n in self.PRIVATE}), \
                mock.patch.object(geo, '_Geometry__encode_tris', return_value=(bytearray(0x20), 1, 3)):
            geo.recode_for_test = geo._Geometry__encode(polygon, **kwargs)
        return mdl.get_material_by_name.return_value.enable_vertex_color

    def test_class_default_applies_without_argument(self):
        self.assertTrue(Geometry.ENABLE_VERTEX_COLORS)
        self.encode().assert_called_once()

    def test_argument_false_leaves_material_alone(self):
        self.encode(vertex_colors=False).assert_not_called()

    def test_argument_true_overrides_class_flag(self):
        with mock.patch.object(Geometry, 'ENABLE_VERTEX_COLORS', False):
            self.encode(vertex_colors=True).assert_called_once()
            self.encode().assert_not_called()


class TestTex0Converter(unittest.TestCase):
    def test_get_converter_prefers_the_configured_one(self):
        sentinel = object()
        with mock.patch.object(Tex0, 'converter', sentinel):
            self.assertIs(sentinel, Tex0.get_converter())

    def test_get_converter_falls_back_to_shared_converter(self):
        with mock.patch.object(Tex0, 'converter', None), \
                mock.patch('abmatt.image_converter.ImgConverter') as img_converter:
            self.assertIs(img_converter.return_value, Tex0.get_converter())


class TestVertexColorImporterFormat(unittest.TestCase):
    def test_encode_format_reaches_the_colors(self):
        geo = mock.Mock()
        geo.get_decoded.return_value.vertices.points = np.zeros((3, 3))
        geo.get_decoded.return_value.vertices.face_indices = np.array([[0, 1, 2]])
        colors = {(0.0, 0.0, 0.0): [((1, 1, 1, 1), None, 0, None, 0)]}
        # name-mangled static helper
        VertexColorImporter._VertexColorImporter__apply_colors_to_geo(colors, geo, (0, 0, 0, 1), 5)
        self.assertEqual(5, geo.get_decoded.return_value.colors.encode_format)


class Bin:
    def __init__(self):
        self.offset = 100

    def advance(self, step):
        self.offset += step


class TestIndirectBlock(unittest.TestCase):
    def unpack(self, stages, ind_mtx_error=None):
        binfile, mat = Bin(), mock.Mock(indirectStages=stages)
        starts = []

        def unpack_matrix(node, bf):
            starts.append(bf.offset)
            if ind_mtx_error:
                raise ind_mtx_error
            bf.advance(15)
            return mock.Mock(node=node)

        with mock.patch.object(unpack_material, 'bp') as bp:
            bp.unpack_alpha_function.return_value = (0,) * 5
            bp.unpack_zmode.return_value = (0,) * 3
            bp.unpack_blend_mode.return_value = (0,) * 9
            bp.unpack_constant_alpha.return_value = (0, 0)
            bp.UnpackIndMtx.side_effect = unpack_matrix
            unpack_material.UnpackMaterial.unpack_matgx(None, mat, binfile)
        return binfile.offset, [s - (binfile.offset - 54) for s in starts], mat

    def test_one_stage_matrices_are_15_bytes_apart(self):
        end, starts, mat = self.unpack(1)
        self.assertEqual([0, 15, 30], starts)
        self.assertEqual(3, len(mat.indirect_matrices))

    def test_two_stage_second_matrix_starts_22_bytes_in(self):
        end, starts, mat = self.unpack(2)
        self.assertEqual([0, 22, 37], starts)
        self.assertEqual(3, len(mat.indirect_matrices))

    def test_block_is_always_54_bytes(self):
        ends = {self.unpack(stages)[0] for stages in (0, 1, 2)}
        self.assertEqual(1, len(ends))

    def test_malformed_block_still_raises(self):
        with self.assertRaises(AssertionError):
            self.unpack(2, AssertionError)


class TestUnusedAnimationOrder(unittest.TestCase):
    def test_unused_animations_keep_file_order(self):
        from types import SimpleNamespace as NS
        from abmatt.brres.lib.unpacking.unpack_brres import UnpackBrres
        names = ['zeta', 'alpha', 'mid', 'beta', 'omega', 'gamma']
        class Anim(list):
            name = 'anim'

        anims = [Anim(NS(name=n) for n in names[:3]), Anim(NS(name=n) for n in names[3:])]
        unpacker = UnpackBrres.__new__(UnpackBrres)
        unpacker.node = NS(models=[])
        out = unpacker.post_unpack_anim(anims, 'materials', 'srt0')
        self.assertEqual(names, [x.name for x in out])


if __name__ == '__main__':
    unittest.main()
