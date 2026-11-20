""" Matching and miscellaneous functions, and clipable interface """

import re
import warnings
from collections.abc import Callable, Iterable, Sequence
from typing import Any, Protocol, TypeVar


class _Named(Protocol):
    name: str


_N = TypeVar('_N', bound=_Named)

BOOLABLE = ["False", "True"]


def _fuzz() -> Any:
    with warnings.catch_warnings():
        # fuzzywuzzy warns when python-Levenshtein (the optional 'speed' extra) is missing
        warnings.simplefilter('ignore', UserWarning)
        from fuzzywuzzy import fuzz
    return fuzz


def fuzzy_match(text: str, group: Iterable[_N], acceptable_ratio: int = 84) -> _N | None:
    fuzz = _fuzz()
    bssf = None
    best_ratio = 0
    lower = text.lower()
    for x in group:
        r = fuzz.ratio(lower, x.name.lower())
        if r > best_ratio:
            best_ratio = r
            bssf = x
    if best_ratio < acceptable_ratio and len(lower) > 2:
        for x in group:
            r = fuzz.partial_ratio(lower, x.name.lower())
            if r > best_ratio:
                best_ratio = r
                bssf = x

    return bssf if best_ratio >= acceptable_ratio else None


def fuzzy_strings(text: str, strings: Iterable[str], acceptable_ratio: int = 84) -> str | None:
    """Same as fuzzy_match except expects group of strings"""
    fuzz = _fuzz()
    bssf = None
    best_ratio = 0
    lower = text.lower()
    for x in strings:
        r = fuzz.ratio(lower, x.lower())
        if r > best_ratio:
            best_ratio = r
            bssf = x
    return bssf if best_ratio > acceptable_ratio else None


def info_default(obj: Any, prefix: str = '', key: str | None = None, indentation: int = 0) -> None:
    s = '  ' * indentation if indentation else ''
    if key:
        print('{}{}: {}:{}'.format(s, prefix, key, obj[key]))
    else:
        s += prefix + ': '
        for x in obj.SETTINGS:
            s += x + ':' + str(obj[x]) + ', '
        print(s[:-2])


def splitKeyVal(value: str, default_key: str = '0') -> tuple[str, str]:
    i = value.find(':')
    if i >= 0:
        key = value[:i]
        try:
            value = value[i + 1:]
        except IndexError:
            raise ValueError('syntax error "{}", val required after colon'.format(value))
    else:
        key = default_key
    return key, value


def validFloat(str: str, min: float, max: float) -> float:
    f = float(str)
    if not min <= f < max:
        raise ValueError("{} is out of range, min: {} max: {}".format(str, min, max))
    return f


def validInt(str: str, min: int = -0x7fffffff, max: int = 0x7fffffff) -> int:
    """ checks if a string is a valid integer """
    i = int(str)
    if not min <= i < max:
        raise ValueError("{} is out of range, min: {} max: {}".format(str, min, max))
    return i


def it_eq(x: Any, y: Any) -> bool:
    """determines if iterable is equal"""
    try:
        iter(x)
        iter(y)
    except TypeError:
        return bool(x == y)
    if len(x) != len(y):
        return False
    # recursively compare, in case of nested iterables
    for i in range(len(x)):
        if not it_eq(x[i], y[i]):
            return False
    return True


def parse_color(color_str: str) -> tuple[int, int, int, int] | list[int] | None:
    """parses color string"""
    if not color_str:
        return 0, 0, 0, 0
    color_str = color_str.strip('()')
    colors = color_str.split(',')
    if len(colors) < 4:
        if color_str == '0':
            return 0, 0, 0, 0
        return None
    intVals = []
    for x in colors:
        i = int(x)
        if not 0 <= i <= 255:
            raise ValueError(f'{color_str} not a valid color string!')
        intVals.append(i)
    return intVals


def validBool(str: str) -> bool:
    """ Checks if its a valid boolean string """
    str = str.lower()
    if str == "false" or not str or str == "0" or "disable" in str or str == "none":
        return False
    elif str == "true" or str == "1" or "enable" in str:
        return True
    raise ValueError("Not a boolean '" + str + "', expected true|false")


# finds index of item, if it is equal to compare index returns -1
# raises error if not found
def indexListItem(list: Sequence[Any], item: Any, compareIndex: int = -2) -> int:
    """ checks for item in list, indexing it """
    for i in range(len(list)):
        if list[i] == item:
            if i != compareIndex:
                return i
            else:
                return -1
    raise ValueError("Invalid setting '" + item + "', Options are: " + str(list))


def parseValStr(value: str) -> list[str]:
    """ Parses tuple/list formed string"""
    values = value.strip('\'[]()').split(",")
    for i in range(len(values)):
        values[i] = values[i].strip()
    return values


""" Matching class """


class Matching:
    PARTIAL_ON_NONE_FOUND = 2
    PARTIAL_ENABLED = 1
    PARTIAL_DISABLED = 0
    REGEX_ON_NONE_FOUND = 2
    REGEX_ENABLED = 1
    REGEX_DISABLED = 0

    direct_group_function: Callable[[str, Iterable[Any], list[Any]], list[Any]]
    regex_group_function: Callable[[str, Iterable[Any], list[Any]], None]

    def __init__(self, case_sensitive: bool = True, partial_matching: int = 2, regex_enable: int = 2) -> None:
        self.case_sensitive = case_sensitive
        self.partial_matching = partial_matching
        self.regex_enable = regex_enable
        self.update()

    def update(self) -> None:
        if self.partial_matching == 1:
            if self.case_sensitive:
                self.direct_group_function = self.match_group_partial_insensitive
                self.regex_group_function = self.regex_group_partial_insensitive
            else:
                self.direct_group_function = self.match_group_partial_sensitive
                self.regex_group_function = self.regex_group_partial_sensitive
        else:
            if self.case_sensitive:
                self.direct_group_function = self.match_group_full_sensitive
                self.regex_group_function = self.regex_group_full_sensitive
            else:
                self.direct_group_function = self.match_group_full_insensitive
                self.regex_group_function = self.regex_group_full_sensitive

    def set_case_sensitive(self, val: str) -> bool:
        try:
            self.case_sensitive = validBool(val)
        except ValueError:
            return False
        self.update()
        return True

    def set_partial_matching(self, val: str) -> bool:
        if val == 'on_none_found':
            self.partial_matching = self.PARTIAL_ON_NONE_FOUND
        try:
            enable = validBool(val)
            self.partial_matching = 1 if enable else 0
        except ValueError:
            return False
        self.update()
        return True

    def set_regex_enable(self, val: str) -> bool:
        if val == 'on_none_found':
            self.regex_enable = self.REGEX_ON_NONE_FOUND
        try:
            enable = validBool(val)
            self.regex_enable = 1 if enable else 0
            self.update()
        except ValueError:
            return False
        return True

    @staticmethod
    def match_group_partial_insensitive(name: str, group: Iterable[Any], results: list[Any]) -> list[Any]:
        name = name.lower()
        for x in group:
            if name in x.name.lower():
                results.append(x)
        return results

    @staticmethod
    def match_group_partial_sensitive(name: str, group: Iterable[Any], results: list[Any]) -> list[Any]:
        for x in group:
            if name in x.name:
                results.append(x)
        return results

    @staticmethod
    def match_group_full_insensitive(name: str, group: Iterable[Any], results: list[Any]) -> list[Any]:
        name = name.lower()
        for x in group:
            if name == x.name.lower():
                results.append(x)
        return results

    @staticmethod
    def match_group_full_sensitive(name: str, group: Iterable[Any], results: list[Any]) -> list[Any]:
        for x in group:
            if name == x.name:
                results.append(x)
        return results

    @staticmethod
    def regex_group_full_insensitive(name: str, group: Iterable[Any], results: list[Any]) -> None:
        try:
            regex = re.compile(name, re.IGNORECASE)
            for x in group:
                if regex.match(x.name):
                    results.append(x)
        except re.error:
            pass

    @staticmethod
    def regex_group_full_sensitive(name: str, group: Iterable[Any], results: list[Any]) -> None:
        try:
            regex = re.compile(name)
            for x in group:
                if regex.match(x.name):
                    results.append(x)
        except re.error:
            pass

    @staticmethod
    def regex_group_partial_insensitive(name: str, group: Iterable[Any], results: list[Any]) -> None:
        try:
            regex = re.compile(name, re.IGNORECASE)
            for x in group:
                if regex.search(x.name):
                    results.append(x)
        except re.error:
            pass

    @staticmethod
    def regex_group_partial_sensitive(name: str, group: Iterable[Any], results: list[Any]) -> None:
        try:
            regex = re.compile(name)
            for x in group:
                if regex.search(x.name):
                    results.append(x)
        except re.error:
            pass

    # finds a name in group, group instances must have .name
    def findAll(self, name: str | None, group: Any) -> Any:
        """ Finds all names matching in a group, either by direct matching or regex if direct fails."""
        if not name or name == "*" or not group:
            return group
        items: list[Any] = []
        # direct matching
        self.direct_group_function(name, group, items)
        # regex
        if self.regex_enable == self.REGEX_ENABLED or not items and self.regex_enable:
            self.regex_group_function(name, group, items)
            if not items and self.partial_matching == self.PARTIAL_ON_NONE_FOUND:
                if self.case_sensitive:
                    self.regex_group_partial_sensitive(name, group, items)
                else:
                    self.regex_group_partial_insensitive(name, group, items)
        # partial if none found?
        elif not items and self.partial_matching == self.PARTIAL_ON_NONE_FOUND:
            if self.case_sensitive:
                self.match_group_partial_sensitive(name, group, items)
            else:
                self.match_group_partial_insensitive(name, group, items)
        return items


MATCHING = Matching()
