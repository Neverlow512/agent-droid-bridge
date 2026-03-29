from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from .models import ScreenElement, ScreenTextResult, TappableElement

BOUNDS_RE = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")

VALID_MODES = frozenset({"tappable", "interactive", "input", "all"})

INPUT_CLASS_FRAGMENTS = ("EditText", "AutoCompleteTextView", "SearchView")


def _parse_bounds(bounds_str: str) -> tuple[int, int, int, int] | None:
    m = BOUNDS_RE.match(bounds_str)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))


def _has_text_descendant(node: ET.Element) -> bool:
    return any(child.get("text", "").strip() for child in node.iter() if child is not node)


def _is_interactive(node: ET.Element) -> bool:
    if node.get("enabled") != "true":
        return False
    return any(
        node.get(attr) == "true"
        for attr in ("clickable", "focusable", "scrollable", "long-clickable")
    )


def _is_input_field(node: ET.Element) -> bool:
    class_attr = node.get("class", "")
    return any(frag in class_attr for frag in INPUT_CLASS_FRAGMENTS)


def _build_xpath(path_parts: list[tuple[str, int]]) -> str:
    if not path_parts:
        return ""
    parts = [f"//{path_parts[0][0]}[{path_parts[0][1]}]"]
    for class_name, idx in path_parts[1:]:
        parts.append(f"/{class_name}[{idx}]")
    return "".join(parts)


def _children_with_paths(
    parent: ET.Element,
    parent_path: list[tuple[str, int]],
) -> list[tuple[ET.Element, list[tuple[str, int]]]]:
    class_counters: dict[str, int] = {}
    items = []
    for child in parent:
        class_name = child.get("class", child.tag)
        class_counters[class_name] = class_counters.get(class_name, 0) + 1
        items.append((child, parent_path + [(class_name, class_counters[class_name])]))
    return items


def parse_elements(xml: str, mode: str) -> list[TappableElement | ScreenElement]:
    if mode not in VALID_MODES:
        raise ValueError(f"Invalid mode: {mode!r}. Must be one of {sorted(VALID_MODES)}")

    root = ET.fromstring(xml)

    results: list[TappableElement | ScreenElement] = []

    stack = _children_with_paths(root, [])
    stack.reverse()

    while stack:
        node, path_parts = stack.pop()

        should_emit = True
        if mode in ("tappable", "interactive"):
            if not _is_interactive(node):
                should_emit = False
        elif mode == "input":
            if not _is_input_field(node):
                should_emit = False

        bounds = _parse_bounds(node.get("bounds", ""))
        if bounds is None:
            should_emit = False

        if should_emit and bounds is not None:
            x1, y1, x2, y2 = bounds
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2
            resource_id = node.get("resource-id", "")
            text = node.get("text", "")
            content_desc = node.get("content-desc", "")

            if mode == "tappable":
                results.append(
                    TappableElement(
                        resource_id=resource_id,
                        text=text,
                        content_desc=content_desc,
                        center_x=center_x,
                        center_y=center_y,
                    )
                )
            else:
                class_name = node.get("class", node.tag)
                results.append(
                    ScreenElement(
                        xpath=_build_xpath(path_parts),
                        resource_id=resource_id,
                        text=text,
                        content_desc=content_desc,
                        class_name=class_name,
                        bounds=(x1, y1, x2, y2),
                        center_x=center_x,
                        center_y=center_y,
                        clickable=node.get("clickable") == "true",
                        focusable=node.get("focusable") == "true",
                        scrollable=node.get("scrollable") == "true",
                        long_clickable=node.get("long-clickable") == "true",
                        checkable=node.get("checkable") == "true",
                        checked=node.get("checked") == "true",
                        enabled=node.get("enabled") == "true",
                        selected=node.get("selected") == "true",
                    )
                )

        children = _children_with_paths(node, path_parts)
        children.reverse()
        stack.extend(children)

    return results


def parse_screen_text(xml: str) -> ScreenTextResult:
    root = ET.fromstring(xml)
    items: list[tuple[int, int, str]] = []
    stack: list[ET.Element] = list(root)
    stack.reverse()
    while stack:
        node = stack.pop()
        text = node.get("text", "").strip()
        content_desc = node.get("content-desc", "").strip()
        if text:
            display_text = text
        elif content_desc and not _has_text_descendant(node):
            display_text = content_desc
        else:
            display_text = ""
        if display_text:
            bounds = _parse_bounds(node.get("bounds", ""))
            if bounds is not None:
                x1, y1, _x2, _y2 = bounds
                items.append((y1, x1, display_text))
        children = list(node)
        children.reverse()
        stack.extend(children)
    items.sort(key=lambda t: (t[0], t[1]))
    deduped: list[tuple[int, int, str]] = []
    for item in items:
        if not deduped or deduped[-1][2] != item[2]:
            deduped.append(item)
    items = deduped
    plain = "\n".join(text for _, _, text in items)
    return ScreenTextResult(plain=plain, total=len(items))
