import pytest

from abmatt.brres.brres import Brres
from abmatt.brres.tex0 import Tex0


@pytest.fixture(autouse=True)
def close_files():
    yield
    Brres.OPEN_FILES.clear()


def test_animations_use_unused_lists():
    brres = Brres('synthetic.brres', read_file=False)
    assert len(brres.get_animations()) == 6
    brres.add_srt_collection('srt')
    brres.add_pat0_collection('pat')
    assert brres.get_animations()[:2] == [['srt'], ['pat']]


def test_rename_texture_moves_map_entry():
    brres = Brres('synthetic.brres', read_file=False)
    tex0 = Tex0('old')
    brres.add_tex0(tex0)
    brres.rename_texture(tex0, 'new')
    assert brres.texture_map == {'new': tex0}


def test_tex0_set_name_renames_through_parent():
    brres = Brres('synthetic.brres', read_file=False)
    tex0 = Tex0('old', brres)
    brres.add_tex0(tex0)
    tex0.set_str('name', 'new')
    assert tex0.name == 'new'
    assert brres.texture_map == {'new': tex0}
