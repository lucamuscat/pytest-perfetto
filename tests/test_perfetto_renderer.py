from typing import List

import pytest
from pyinstrument.frame import Frame

from pytest_perfetto.perfetto_renderer import RootFrameCannotBeHoistedException, hoist


def test_when_hoist__then_grandchild_frame_becomes_parent_sibling() -> None:
    root_frame: Frame = Frame(identifier_or_frame_info="root")
    grandparent_frame: Frame = Frame(identifier_or_frame_info="grandparent")
    parent_to_be_hoisted: Frame = Frame(identifier_or_frame_info="hoist me")
    grandchildren: List[Frame] = [
        Frame(identifier_or_frame_info="grandchild1"),
        Frame(identifier_or_frame_info="grandchild2"),
    ]

    parent_to_be_hoisted.add_children(grandchildren)
    grandparent_frame.add_child(parent_to_be_hoisted)
    root_frame.add_child(grandparent_frame)

    hoist(parent_to_be_hoisted)

    assert list(grandparent_frame.children) == grandchildren


def test_given_root__when_hoist__then_raise_exception() -> None:
    root_frame = Frame(identifier_or_frame_info="root")
    children = [Frame(identifier_or_frame_info="1"), Frame(identifier_or_frame_info="2")]
    root_frame.add_children(children)

    with pytest.raises(RootFrameCannotBeHoistedException):
        hoist(root_frame)


def test_given_no_grand_children__when_hoist__then_remove_frame() -> None:
    root_frame = Frame(identifier_or_frame_info="root")
    frame_to_hoist = Frame(identifier_or_frame_info="hoist me")
    root_frame.add_child(frame_to_hoist)
    hoist(frame_to_hoist)

    assert len(root_frame.children) == 0


def test_given_siblings__when_hoist__then_hoisted_children_are_correctly_ordered() -> None:
    root_frame = Frame(identifier_or_frame_info="root")
    grandparent = Frame(identifier_or_frame_info="grandparent")
    parents = [
        Frame(identifier_or_frame_info="parent1"),
        Frame(identifier_or_frame_info="parent2"),
        Frame(identifier_or_frame_info="parent3"),
    ]
    nieces = [Frame(identifier_or_frame_info="powder"), Frame(identifier_or_frame_info="violet")]

    parents[1].add_children(nieces)
    grandparent.add_children(parents)
    root_frame.add_child(grandparent)

    hoist(parents[1])

    # TODO: Merge into a single assertion.
    assert grandparent.children[1].identifier == "powder"
    assert grandparent.children[2].identifier == "violet"
    assert grandparent.children[3].identifier == "parent3"
