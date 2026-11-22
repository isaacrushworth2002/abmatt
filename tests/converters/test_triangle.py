import unittest
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from abmatt.converters.triangle import TriangleSet


def grid(n, base):
    """An n x n grid of quads as triangles, vertices (base + i, base + i) so two grids share none."""
    def v(x, y):
        i = base + y * (n + 1) + x
        return (i, i)
    tris = []
    for y in range(n):
        for x in range(n):
            tris.append([v(x, y), v(x + 1, y), v(x, y + 1)])
            tris.append([v(x + 1, y), v(x + 1, y + 1), v(x, y + 1)])
    return np.array(tris, dtype=np.uint64)


class TriangleSetTest(unittest.TestCase):
    def test_sets_do_not_share_edges(self):
        a = TriangleSet(grid(8, 0))
        b = TriangleSet(grid(8, 10000))
        for tri_set in (a, b):
            strips, count, _, _ = tri_set.get_tri_strips()
            self.assertEqual(128, count)
            self.assertTrue(strips)

    def test_strips_in_threads(self):
        sets = [TriangleSet(grid(30, i * 100000)) for i in range(8)]
        with ThreadPoolExecutor(8) as pool:
            results = list(pool.map(lambda s: s.get_tri_strips(), sets))
        self.assertEqual([1800] * 8, [r[1] for r in results])

    def test_sets_built_in_threads(self):
        def run(i):
            return TriangleSet(grid(30, i * 100000)).get_tri_strips()[1]
        with ThreadPoolExecutor(8) as pool:
            counts = list(pool.map(run, range(16)))
        self.assertEqual([1800] * 16, counts)
