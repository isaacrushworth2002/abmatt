import os
import shutil

import pytest


def pytest_collection_modifyitems(config, items):
    no_wimgt = pytest.mark.skip(reason="wimgt is not on the PATH")
    no_disc = pytest.mark.skip(reason="set ABMATT_DISC to a local disc dump to run")
    have_wimgt = shutil.which('wimgt') is not None
    have_disc = bool(os.environ.get('ABMATT_DISC'))
    for item in items:
        if 'needs_wimgt' in item.keywords and not have_wimgt:
            item.add_marker(no_wimgt)
        if 'needs_disc' in item.keywords and not have_disc:
            item.add_marker(no_disc)
