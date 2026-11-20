from __future__ import annotations

import os
from collections.abc import Iterable, MutableMapping, Sequence
from typing import Any, Protocol, TypeVar

from abmatt.autofix import AutoFix



class _Indexed(Protocol):
    index: int


_I = TypeVar('_I', bound=_Indexed)


def get_name_mapping(group: Iterable[Any]) -> dict[str, Any]:
    mapper = {}
    for x in group:
        mapper[x.name] = x
    return mapper


def get_item_by_index(group: Sequence[_I], index: int) -> _I | None:
    try:
        item = group[index]
        if item.index == index:
            return item
    except IndexError:
        pass
    for x in group:
        if x.index == index:
            return x
    return None


class Packable:
    def unpack(self, binfile: Any) -> None:
        raise NotImplementedError()

    def pack(self, binfile: Any) -> None:
        raise NotImplementedError()


class Node:
    """A node with name and parent"""

    def __init__(self, name: str, parent: Any, binfile: Any = None) -> None:
        # parent is whichever Node owns this one (Brres, Mdl0, Material, ...), so it is not narrowed here
        self.parent = parent
        self.name = name
        if binfile is None:
            self.begin()

    def begin(self) -> None:
        pass

    def __deepcopy__(self, memodict: Any = None) -> Any:
        raise NotImplementedError()

    def __eq__(self, other: object) -> bool:
        return other is not None and type(self) == type(other) and self.name == other.name

    def __str__(self) -> str:
        return self.name

    def __hash__(self) -> int:
        return hash(self.get_full_path())

    def get_full_path(self) -> str:
        return os.path.join(self.parent.get_full_path(), self.name) if self.parent else self.name

    def link_parent(self, parent: Any) -> None:
        self.parent = parent


class ClipableObserver:
    """Receives updates from clipable"""

    def on_node_update(self, node: Any) -> None:
        pass

    def on_child_update(self, child: Any) -> None:  # might not have children
        pass

    def on_rename_update(self, node: Any, old_name: str) -> None:
        pass


class Clipable(Node):
    """Clipable interface"""
    OVERWRITE_MODE = False

    @property
    def SETTINGS(self) -> Sequence[str]:
        raise NotImplementedError()

    def __init__(self, name: str, parent: Any, binfile: Any) -> None:
        self.is_modified = False
        self.observers: list[ClipableObserver] | None = None  # also make this observable
        super(Clipable, self).__init__(name, parent, binfile)

    def rename(self, name: str) -> bool:
        if name != self.name:
            old_name = self.name
            self.name = name
            self.mark_modified(False)
            self.notify_rename(old_name)
            return True
        return False

    # ------------------------------------- OBSERVERS ----------------------------
    def notify_rename(self, old_name: str) -> None:
        if self.observers:
            for x in self.observers:
                x.on_rename_update(self, old_name)
        self.notify_parent_observers()

    def notify_observers(self) -> None:
        if self.observers:
            for x in self.observers:
                x.on_node_update(self)
        self.notify_parent_observers()

    def notify_parent_observers(self) -> None:
        parent = self.parent
        if parent and parent.observers:
            for x in parent.observers:
                x.on_child_update(self)

    def register_observer(self, observer: ClipableObserver) -> None:
        if self.observers is None:
            self.observers = [observer]
        elif observer not in self.observers:
            self.observers.append(observer)

    def unregister(self, observer: ClipableObserver) -> None:
        try:
            self.observers.remove(observer)  # type: ignore[union-attr]  # AttributeError when never registered
        except ValueError as e:
            pass

    # ---------------------------------------------- CLIPBOARD -------------------------------------------
    @staticmethod
    def paste_group(paste_group: Iterable[Any], clip_group: Iterable[Any]) -> None:
        for x in clip_group:
            name = x.name
            for y in paste_group:
                if y.name == name:
                    y.paste(x)
                    break

    def set_str(self, key: str, value: str) -> bool | None:
        raise NotImplementedError()

    def get_str(self, key: str) -> str:
        raise NotImplementedError()

    def clip(self, clipboard: MutableMapping[str, Any]) -> None:
        clipboard[self.name] = self

    def clip_find(self, clipboard: MutableMapping[str, Any]) -> Any:
        return clipboard.get(self.name)

    def paste(self, item: Any) -> None:
        raise NotImplementedError()

    def mark_modified(self, notify_observers: bool = True) -> None:
        if notify_observers:
            self.notify_observers()
        if not self.is_modified:
            self.is_modified = True
            if self.parent:
                self.parent.mark_modified(False)  # marks parent modified but does not notify

    def _mark_unmodified_group(self, group: Iterable[Any]) -> None:
        for x in group:
            x.mark_unmodified()

    def mark_unmodified(self) -> None:
        """
        After saving a file, call this on children to reset modification markings
        parents need to call this on their children
        """
        self.is_modified = False

    def get_texture_map(self) -> Any:
        if self.parent:
            return self.parent.get_texture_map()

    def info(self, key: str = '', indentation_level: int = 0) -> None:
        if not key:
            m = max(3, len(self.SETTINGS))
            for i in range(m):
                setting = self.SETTINGS[i]
                key += setting + ':' + self.get_str(setting) + ' '
        else:
            key += ':' + self.get_str(key)
        start = '>' + indentation_level * '  '
        AutoFix.info('{}{}> {}'.format(start, self.name, key), 1)

    def get_full_path(self) -> str:
        return os.path.join(self.parent.get_full_path(), self.name)
