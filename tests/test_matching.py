import pytest

from abmatt.brres.lib.matching import Matching


class Named:
    def __init__(self, name):
        self.name = name


GROUP = [Named('Body'), Named('body_alt'), Named('Wheel')]


@pytest.mark.parametrize('partial', [0, 1])
def test_case_sensitive_flag_picks_functions(partial):
    sensitive = Matching(True, partial, 0)
    insensitive = Matching(False, partial, 0)
    assert sensitive.findAll('body', GROUP) == ([] if not partial else [GROUP[1]])
    names = [x.name for x in insensitive.findAll('body', GROUP)]
    assert names == (['Body'] if not partial else ['Body', 'body_alt'])


@pytest.mark.parametrize('partial', [0, 1])
def test_regex_follows_case_sensitivity(partial):
    sensitive = Matching(True, partial, 0)
    insensitive = Matching(False, partial, 0)
    assert [x.name for x in sensitive.regex_group_function('body', GROUP, [])] == ['body_alt']
    assert [x.name for x in insensitive.regex_group_function('body', GROUP, [])] == ['Body', 'body_alt']


def test_regex_group_functions_return_results():
    results: list[Named] = []
    assert Matching.regex_group_full_sensitive('Body', GROUP, results) is results
    assert results == [GROUP[0]]
    assert Matching.regex_group_partial_insensitive('(', GROUP, []) == []
