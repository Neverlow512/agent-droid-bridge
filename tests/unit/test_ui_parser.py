from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from agent_droid_bridge.models import ScreenElement, ScreenTextResult, TappableElement
from agent_droid_bridge.ui_parser import (
    _build_xpath,
    _parse_bounds,
    parse_elements,
    parse_screen_text,
)

MISC_DIR = Path(__file__).parent.parent.parent / "misc"

EMPTY_XML = '<?xml version="1.0" encoding="UTF-8"?><hierarchy rotation="0"></hierarchy>'

SIBLINGS_XML = """<hierarchy rotation="0">
  <android.widget.FrameLayout class="android.widget.FrameLayout"
      bounds="[0,0][1080,2400]" clickable="true" focusable="true"
      scrollable="false" long-clickable="false" text="" content-desc=""
      resource-id="" checkable="false" checked="false" enabled="true" selected="false">
    <android.widget.Button class="android.widget.Button" bounds="[0,0][540,100]"
        clickable="true" focusable="true" scrollable="false" long-clickable="false"
        text="First" content-desc="" resource-id="" checkable="false" checked="false"
        enabled="true" selected="false" />
    <android.widget.Button class="android.widget.Button" bounds="[540,0][1080,100]"
        clickable="true" focusable="true" scrollable="false" long-clickable="false"
        text="Second" content-desc="" resource-id="" checkable="false" checked="false"
        enabled="true" selected="false" />
  </android.widget.FrameLayout>
</hierarchy>"""

NO_BOUNDS_XML = """<hierarchy rotation="0">
  <android.widget.FrameLayout class="android.widget.FrameLayout"
      clickable="true" focusable="false" scrollable="false" long-clickable="false"
      text="" content-desc="" resource-id="" checkable="false" checked="false"
      enabled="true" selected="false">
  </android.widget.FrameLayout>
</hierarchy>"""


def _load(name: str) -> str:
    return (MISC_DIR / name).read_text(encoding="utf-8")


class TestParseBounds:
    def test_valid_bounds(self) -> None:
        result = _parse_bounds("[100,200][300,400]")
        assert result == (100, 200, 300, 400)

    def test_invalid_bounds_returns_none(self) -> None:
        assert _parse_bounds("invalid") is None

    def test_empty_string_returns_none(self) -> None:
        assert _parse_bounds("") is None


class TestCenterCalculation:
    def test_center_x_y(self) -> None:
        result = _parse_bounds("[100,200][300,400]")
        assert result is not None
        x1, y1, x2, y2 = result
        assert (x1 + x2) // 2 == 200
        assert (y1 + y2) // 2 == 300


class TestBuildXpath:
    def test_single_element(self) -> None:
        result = _build_xpath([("android.widget.FrameLayout", 1)])
        assert result == "//android.widget.FrameLayout[1]"

    def test_nested_elements(self) -> None:
        parts = [
            ("android.widget.FrameLayout", 1),
            ("android.widget.LinearLayout", 1),
            ("android.widget.Button", 2),
        ]
        result = _build_xpath(parts)
        expected = (
            "//android.widget.FrameLayout[1]"
            "/android.widget.LinearLayout[1]"
            "/android.widget.Button[2]"
        )
        assert result == expected

    def test_empty_parts(self) -> None:
        assert _build_xpath([]) == ""


class TestInvalidMode:
    def test_invalid_mode_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            parse_elements(EMPTY_XML, "bogus")


class TestMalformedXML:
    def test_malformed_xml_raises_parse_error(self) -> None:
        with pytest.raises(ET.ParseError):
            parse_elements("<not valid xml<<<", "all")


class TestEmptyHierarchy:
    def test_tappable_returns_empty(self) -> None:
        assert parse_elements(EMPTY_XML, "tappable") == []

    def test_interactive_returns_empty(self) -> None:
        assert parse_elements(EMPTY_XML, "interactive") == []

    def test_input_returns_empty(self) -> None:
        assert parse_elements(EMPTY_XML, "input") == []

    def test_all_returns_empty(self) -> None:
        assert parse_elements(EMPTY_XML, "all") == []


class TestTappableMode:
    def test_returns_only_tappable_elements(self) -> None:
        xml = _load("current_screen.xml")
        results = parse_elements(xml, "tappable")
        assert len(results) > 0
        assert all(isinstance(e, TappableElement) for e in results)

    def test_all_have_center_coordinates(self) -> None:
        xml = _load("current_screen.xml")
        results = parse_elements(xml, "tappable")
        for e in results:
            assert isinstance(e.center_x, int)
            assert isinstance(e.center_y, int)


class TestInteractiveMode:
    def test_returns_only_screen_elements(self) -> None:
        xml = _load("current_screen.xml")
        results = parse_elements(xml, "interactive")
        assert all(isinstance(e, ScreenElement) for e in results)

    def test_same_count_as_tappable(self) -> None:
        xml = _load("current_screen.xml")
        tappable = parse_elements(xml, "tappable")
        interactive = parse_elements(xml, "interactive")
        assert len(tappable) == len(interactive)

    def test_xpath_is_non_empty(self) -> None:
        xml = _load("current_screen.xml")
        results = parse_elements(xml, "interactive")
        assert len(results) > 0
        for e in results:
            assert isinstance(e, ScreenElement)
            assert e.xpath != ""

    def test_bounds_is_4_tuple(self) -> None:
        xml = _load("current_screen.xml")
        results = parse_elements(xml, "interactive")
        assert len(results) > 0
        first = results[0]
        assert isinstance(first, ScreenElement)
        assert len(first.bounds) == 4
        assert all(isinstance(v, int) for v in first.bounds)


class TestInputMode:
    def test_returns_edit_text_elements_from_after_country_select(self) -> None:
        xml = _load("after_country_select.xml")
        results = parse_elements(xml, "input")
        assert len(results) > 0
        for e in results:
            assert isinstance(e, ScreenElement)
            assert any(frag in e.class_name for frag in ("EditText", "AutoCompleteTextView"))

    def test_current_screen_has_edit_text(self) -> None:
        xml = _load("current_screen.xml")
        results = parse_elements(xml, "input")
        assert len(results) > 0


class TestAllMode:
    def test_returns_screen_elements(self) -> None:
        xml = _load("current_screen.xml")
        results = parse_elements(xml, "all")
        assert all(isinstance(e, ScreenElement) for e in results)

    def test_count_gte_tappable(self) -> None:
        xml = _load("current_screen.xml")
        tappable = parse_elements(xml, "tappable")
        all_results = parse_elements(xml, "all")
        assert len(all_results) >= len(tappable)


class TestSiblingIndexing:
    def test_two_buttons_get_indices_1_and_2(self) -> None:
        results = parse_elements(SIBLINGS_XML, "interactive")
        button_results = [
            e for e in results if isinstance(e, ScreenElement) and "Button" in e.class_name
        ]
        xpaths = [e.xpath for e in button_results]
        assert any(x.endswith("android.widget.Button[1]") for x in xpaths)
        assert any(x.endswith("android.widget.Button[2]") for x in xpaths)

    def test_all_mode_includes_parent_and_children(self) -> None:
        results = parse_elements(SIBLINGS_XML, "all")
        assert len(results) == 3


class TestNoBoundsSkipped:
    def test_node_without_bounds_is_skipped(self) -> None:
        results = parse_elements(NO_BOUNDS_XML, "all")
        assert results == []


DISABLED_ELEMENT_XML = """<hierarchy rotation="0">
  <android.widget.FrameLayout class="android.widget.FrameLayout"
      bounds="[0,0][1080,2400]" clickable="false" focusable="false"
      scrollable="false" long-clickable="false" text="" content-desc=""
      resource-id="" checkable="false" checked="false" enabled="true" selected="false">
    <android.widget.Button class="android.widget.Button" bounds="[0,0][540,100]"
        clickable="true" focusable="true" scrollable="false" long-clickable="false"
        text="DisabledBtn" content-desc="" resource-id="" checkable="false" checked="false"
        enabled="false" selected="false" />
  </android.widget.FrameLayout>
</hierarchy>"""

SEARCH_VIEW_XML = """<hierarchy rotation="0">
  <android.widget.FrameLayout class="android.widget.FrameLayout"
      bounds="[0,0][1080,2400]" clickable="false" focusable="false"
      scrollable="false" long-clickable="false" text="" content-desc=""
      resource-id="" checkable="false" checked="false" enabled="true" selected="false">
    <android.widget.SearchView class="android.widget.SearchView"
        bounds="[0,0][1080,100]" clickable="false" focusable="true"
        scrollable="false" long-clickable="false" text="" content-desc=""
        resource-id="com.example:id/search" checkable="false" checked="false"
        enabled="true" selected="false" />
  </android.widget.FrameLayout>
</hierarchy>"""


class TestDisabledElementExcluded:
    def test_disabled_clickable_not_in_tappable(self) -> None:
        results = parse_elements(DISABLED_ELEMENT_XML, "tappable")
        assert all(e.text != "DisabledBtn" for e in results)
        assert len(results) == 0


class TestSearchViewInInputMode:
    def test_search_view_appears_in_input_mode(self) -> None:
        results = parse_elements(SEARCH_VIEW_XML, "input")
        assert len(results) == 1
        assert isinstance(results[0], ScreenElement)
        assert "SearchView" in results[0].class_name


EMPTY_TEXT_XML = '<?xml version="1.0" encoding="UTF-8"?><hierarchy rotation="0"></hierarchy>'

TEXT_ONLY_XML = """<hierarchy rotation="0">
  <android.widget.TextView class="android.widget.TextView"
      bounds="[0,100][540,200]" text="Hello" content-desc=""
      clickable="false" focusable="false" scrollable="false"
      long-clickable="false" enabled="true" selected="false"
      resource-id="" checkable="false" checked="false" />
  <android.widget.TextView class="android.widget.TextView"
      bounds="[0,200][540,300]" text="" content-desc="Back button"
      clickable="true" focusable="true" scrollable="false"
      long-clickable="false" enabled="true" selected="false"
      resource-id="" checkable="false" checked="false" />
  <android.widget.TextView class="android.widget.TextView"
      bounds="[0,50][540,100]" text="Title" content-desc=""
      clickable="false" focusable="false" scrollable="false"
      long-clickable="false" enabled="true" selected="false"
      resource-id="" checkable="false" checked="false" />
</hierarchy>"""


class TestParseScreenText:
    def test_returns_screen_text_result(self) -> None:
        result = parse_screen_text(_load("current_screen.xml"))
        assert isinstance(result, ScreenTextResult)
        assert result.total > 0
        assert len(result.plain.split("\n")) == result.total

    def test_plain_is_newline_joined(self) -> None:
        result = parse_screen_text(TEXT_ONLY_XML)
        assert result.total == 3
        assert "\n" in result.plain

    def test_sorted_top_to_bottom(self) -> None:
        result = parse_screen_text(TEXT_ONLY_XML)
        lines = result.plain.split("\n")
        assert lines[0] == "Title"
        assert lines[1] == "Hello"
        assert lines[2] == "Back button"

    def test_prefers_text_over_content_desc(self) -> None:
        xml = """<hierarchy rotation="0">
          <android.widget.Button class="android.widget.Button"
              bounds="[0,0][540,100]" text="Submit" content-desc="Submit button"
              clickable="true" focusable="true" scrollable="false"
              long-clickable="false" enabled="true" selected="false"
              resource-id="" checkable="false" checked="false" />
        </hierarchy>"""
        result = parse_screen_text(xml)
        assert result.total == 1
        assert result.plain == "Submit"

    def test_falls_back_to_content_desc(self) -> None:
        xml = """<hierarchy rotation="0">
          <android.widget.ImageButton class="android.widget.ImageButton"
              bounds="[0,0][100,100]" text="" content-desc="Back"
              clickable="true" focusable="true" scrollable="false"
              long-clickable="false" enabled="true" selected="false"
              resource-id="" checkable="false" checked="false" />
        </hierarchy>"""
        result = parse_screen_text(xml)
        assert result.total == 1
        assert result.plain == "Back"

    def test_parent_content_desc_skipped_when_children_have_text(self) -> None:
        xml = """<hierarchy rotation="0">
          <android.widget.LinearLayout class="android.widget.LinearLayout"
              bounds="[0,0][540,200]" text="" content-desc="United States country code +1"
              clickable="false" focusable="false" scrollable="false"
              long-clickable="false" enabled="true" selected="false"
              resource-id="" checkable="false" checked="false">
            <android.widget.TextView class="android.widget.TextView"
                bounds="[0,0][540,100]" text="United States" content-desc=""
                clickable="false" focusable="false" scrollable="false"
                long-clickable="false" enabled="true" selected="false"
                resource-id="" checkable="false" checked="false" />
          </android.widget.LinearLayout>
        </hierarchy>"""
        result = parse_screen_text(xml)
        assert result.total == 1
        assert result.plain == "United States"

    def test_skips_nodes_with_no_text(self) -> None:
        xml = """<hierarchy rotation="0">
          <android.widget.FrameLayout class="android.widget.FrameLayout"
              bounds="[0,0][1080,2400]" text="" content-desc=""
              clickable="false" focusable="false" scrollable="false"
              long-clickable="false" enabled="true" selected="false"
              resource-id="" checkable="false" checked="false" />
        </hierarchy>"""
        result = parse_screen_text(xml)
        assert result.total == 0
        assert result.plain == ""

    def test_empty_screen(self) -> None:
        result = parse_screen_text(EMPTY_TEXT_XML)
        assert result.total == 0
        assert result.plain == ""

    def test_malformed_xml_raises(self) -> None:
        with pytest.raises(ET.ParseError):
            parse_screen_text("not xml at all")

    def test_parent_and_child_same_text_deduplicated(self) -> None:
        xml = """<hierarchy rotation="0">
          <android.widget.Button class="android.widget.Button"
              bounds="[0,0][540,100]" text="Submit" content-desc=""
              clickable="true" focusable="true" scrollable="false"
              long-clickable="false" enabled="true" selected="false"
              resource-id="" checkable="false" checked="false">
            <android.widget.TextView class="android.widget.TextView"
                bounds="[10,10][530,90]" text="Submit" content-desc=""
                clickable="false" focusable="false" scrollable="false"
                long-clickable="false" enabled="true" selected="false"
                resource-id="" checkable="false" checked="false" />
          </android.widget.Button>
        </hierarchy>"""
        result = parse_screen_text(xml)
        assert result.total == 1
        assert result.plain == "Submit"

    def test_real_xml_plain_is_readable(self) -> None:
        result = parse_screen_text(_load("current_screen.xml"))
        assert "\n" in result.plain
        assert len(result.plain) > 0
