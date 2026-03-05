"""Pure XML rendering functions for desk phone XML apps.

Supports three manufacturers:
  - Yealink: YealinkIPPhone* XML
  - Cisco: CiscoIPPhone* XML Services
  - Polycom: XHTML micro-browser pages

Data in → XML string out. No database access, no side effects.
"""

from __future__ import annotations

from dataclasses import dataclass
from xml.etree.ElementTree import Element, SubElement, tostring

# ── Data structures ──────────────────────────────────────────────────


@dataclass(frozen=True)
class MenuItem:
    prompt: str
    uri: str


@dataclass(frozen=True)
class DirEntry:
    name: str
    number: str


@dataclass(frozen=True)
class StatusRow:
    label: str
    value: str
    dial_uri: str | None = None


@dataclass(frozen=True)
class PageInfo:
    page: int
    page_size: int
    total: int

    @property
    def total_pages(self) -> int:
        if self.total == 0:
            return 1
        return (self.total + self.page_size - 1) // self.page_size

    @property
    def has_prev(self) -> bool:
        return self.page > 1

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages


# ── XML helpers ──────────────────────────────────────────────────────


def _xml_decl() -> str:
    return '<?xml version="1.0" encoding="ISO-8859-1"?>\n'


def _indent(elem: Element, level: int = 0) -> None:
    """Add whitespace indentation to an XML tree for pretty-printing."""
    indent = "\n" + "  " * level
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = indent + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = indent
        for child in elem:
            _indent(child, level + 1)
        if not child.tail or not child.tail.strip():  # type: ignore[possibly-undefined]
            child.tail = indent  # type: ignore[possibly-undefined]
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = indent


def _to_xml(root: Element) -> str:
    _indent(root)
    return _xml_decl() + tostring(root, encoding="unicode")


def _polycom_html(title: str, body_html: str) -> str:
    return (
        _xml_decl()
        + "<html><head><title>"
        + _esc(title)
        + "</title></head><body>"
        + body_html
        + "</body></html>"
    )


def _esc(text: str) -> str:
    """Escape for XML text content."""
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )


# ── Dispatcher functions ────────────────────────────────────────────


def render_menu(manufacturer: str, title: str, items: list[MenuItem], base_url: str = "") -> str:
    if manufacturer == "cisco":
        return _cisco_menu(title, items)
    if manufacturer == "polycom":
        return _polycom_menu(title, items)
    return _yealink_menu(title, items)


def render_directory(
    manufacturer: str,
    title: str,
    entries: list[DirEntry],
    page_info: PageInfo | None = None,
    base_url: str = "",
) -> str:
    if manufacturer == "cisco":
        return _cisco_directory(title, entries, page_info, base_url)
    if manufacturer == "polycom":
        return _polycom_directory(title, entries, page_info, base_url)
    return _yealink_directory(title, entries, page_info, base_url)


def render_text_screen(manufacturer: str, title: str, text: str) -> str:
    if manufacturer == "cisco":
        return _cisco_text(title, text)
    if manufacturer == "polycom":
        return _polycom_text(title, text)
    return _yealink_text(title, text)


def render_input_screen(
    manufacturer: str,
    title: str,
    prompt: str,
    submit_url: str,
    field_name: str,
) -> str:
    if manufacturer == "cisco":
        return _cisco_input(title, prompt, submit_url, field_name)
    if manufacturer == "polycom":
        return _polycom_input(title, prompt, submit_url, field_name)
    return _yealink_input(title, prompt, submit_url, field_name)


def render_status_list(manufacturer: str, title: str, rows: list[StatusRow]) -> str:
    if manufacturer == "cisco":
        return _cisco_status_list(title, rows)
    if manufacturer == "polycom":
        return _polycom_status_list(title, rows)
    return _yealink_status_list(title, rows)


# ── Yealink renderers ───────────────────────────────────────────────


def _yealink_menu(title: str, items: list[MenuItem]) -> str:
    root = Element("YealinkIPPhoneTextMenu")
    SubElement(root, "Title").text = title
    for item in items:
        mi = SubElement(root, "MenuItem")
        SubElement(mi, "Prompt").text = item.prompt
        SubElement(mi, "URI").text = item.uri
    return _to_xml(root)


def _yealink_directory(
    title: str,
    entries: list[DirEntry],
    page_info: PageInfo | None,
    base_url: str,
) -> str:
    root = Element("YealinkIPPhoneDirectory")
    SubElement(root, "Title").text = title
    for entry in entries:
        di = SubElement(root, "DirectoryEntry")
        SubElement(di, "Name").text = entry.name
        SubElement(di, "Telephone").text = entry.number
    if page_info:
        _yealink_softkeys_pagination(root, page_info, base_url)
    return _to_xml(root)


def _yealink_text(title: str, text: str) -> str:
    root = Element("YealinkIPPhoneTextScreen")
    SubElement(root, "Title").text = title
    SubElement(root, "Text").text = text
    return _to_xml(root)


def _yealink_input(title: str, prompt: str, submit_url: str, field_name: str) -> str:
    root = Element("YealinkIPPhoneInput")
    SubElement(root, "Title").text = title
    SubElement(root, "Prompt").text = prompt
    SubElement(root, "URL").text = submit_url
    inp = SubElement(root, "InputItem")
    SubElement(inp, "DisplayName").text = prompt
    SubElement(inp, "QueryStringParam").text = field_name
    SubElement(inp, "InputFlags").text = "a"
    SubElement(inp, "DefaultValue").text = ""
    return _to_xml(root)


def _yealink_status_list(title: str, rows: list[StatusRow]) -> str:
    root = Element("YealinkIPPhoneTextMenu")
    SubElement(root, "Title").text = title
    for row in rows:
        mi = SubElement(root, "MenuItem")
        SubElement(mi, "Prompt").text = f"{row.label}: {row.value}"
        SubElement(mi, "URI").text = row.dial_uri or ""
    return _to_xml(root)


def _yealink_softkeys_pagination(root: Element, page_info: PageInfo, base_url: str) -> None:
    if page_info.has_prev:
        sk = SubElement(root, "SoftKey", index="1")
        SubElement(sk, "Label").text = "Previous"
        SubElement(sk, "URI").text = f"{base_url}?page={page_info.page - 1}"
    if page_info.has_next:
        sk = SubElement(root, "SoftKey", index="2")
        SubElement(sk, "Label").text = "Next"
        SubElement(sk, "URI").text = f"{base_url}?page={page_info.page + 1}"


# ── Cisco renderers ─────────────────────────────────────────────────


def _cisco_menu(title: str, items: list[MenuItem]) -> str:
    root = Element("CiscoIPPhoneMenu")
    SubElement(root, "Title").text = title
    for item in items:
        mi = SubElement(root, "MenuItem")
        SubElement(mi, "Name").text = item.prompt
        SubElement(mi, "URL").text = item.uri
    return _to_xml(root)


def _cisco_directory(
    title: str,
    entries: list[DirEntry],
    page_info: PageInfo | None,
    base_url: str,
) -> str:
    root = Element("CiscoIPPhoneDirectory")
    SubElement(root, "Title").text = title
    for entry in entries:
        de = SubElement(root, "DirectoryEntry")
        SubElement(de, "Name").text = entry.name
        SubElement(de, "Telephone").text = entry.number
    if page_info:
        _cisco_softkeys_pagination(root, page_info, base_url)
    return _to_xml(root)


def _cisco_text(title: str, text: str) -> str:
    root = Element("CiscoIPPhoneText")
    SubElement(root, "Title").text = title
    SubElement(root, "Text").text = text
    return _to_xml(root)


def _cisco_input(title: str, prompt: str, submit_url: str, field_name: str) -> str:
    root = Element("CiscoIPPhoneInput")
    SubElement(root, "Title").text = title
    SubElement(root, "Prompt").text = prompt
    SubElement(root, "URL").text = submit_url
    inp = SubElement(root, "InputItem")
    SubElement(inp, "DisplayName").text = prompt
    SubElement(inp, "QueryStringParam").text = field_name
    SubElement(inp, "InputFlags").text = "A"
    SubElement(inp, "DefaultValue").text = ""
    return _to_xml(root)


def _cisco_status_list(title: str, rows: list[StatusRow]) -> str:
    root = Element("CiscoIPPhoneMenu")
    SubElement(root, "Title").text = title
    for row in rows:
        mi = SubElement(root, "MenuItem")
        SubElement(mi, "Name").text = f"{row.label}: {row.value}"
        SubElement(mi, "URL").text = row.dial_uri or ""
    return _to_xml(root)


def _cisco_softkeys_pagination(root: Element, page_info: PageInfo, base_url: str) -> None:
    if page_info.has_prev:
        sk = SubElement(root, "SoftKeyItem")
        SubElement(sk, "Name").text = "Previous"
        SubElement(sk, "URL").text = f"{base_url}?page={page_info.page - 1}"
        SubElement(sk, "Position").text = "1"
    if page_info.has_next:
        sk = SubElement(root, "SoftKeyItem")
        SubElement(sk, "Name").text = "Next"
        SubElement(sk, "URL").text = f"{base_url}?page={page_info.page + 1}"
        SubElement(sk, "Position").text = "2"


# ── Polycom renderers ───────────────────────────────────────────────


def _polycom_menu(title: str, items: list[MenuItem]) -> str:
    lines = [f"<b>{_esc(title)}</b><br/>"]
    for item in items:
        lines.append(f'<a href="{_esc(item.uri)}">{_esc(item.prompt)}</a><br/>')
    return _polycom_html(title, "\n".join(lines))


def _polycom_directory(
    title: str,
    entries: list[DirEntry],
    page_info: PageInfo | None,
    base_url: str,
) -> str:
    lines = [f"<b>{_esc(title)}</b><br/>"]
    for entry in entries:
        lines.append(
            f'<a href="tel:{_esc(entry.number)}">{_esc(entry.name)} ({_esc(entry.number)})</a><br/>'
        )
    if page_info:
        nav = []
        if page_info.has_prev:
            nav.append(f'<a href="{_esc(base_url)}?page={page_info.page - 1}">Previous</a>')
        if page_info.has_next:
            nav.append(f'<a href="{_esc(base_url)}?page={page_info.page + 1}">Next</a>')
        if nav:
            lines.append(" | ".join(nav))
    return _polycom_html(title, "\n".join(lines))


def _polycom_text(title: str, text: str) -> str:
    body = f"<b>{_esc(title)}</b><br/><p>{_esc(text)}</p>"
    return _polycom_html(title, body)


def _polycom_input(title: str, prompt: str, submit_url: str, field_name: str) -> str:
    body = (
        f"<b>{_esc(title)}</b><br/>"
        f'<form method="get" action="{_esc(submit_url)}">'
        f"<p>{_esc(prompt)}</p>"
        f'<input type="text" name="{_esc(field_name)}"/>'
        f'<input type="submit" value="Search"/>'
        f"</form>"
    )
    return _polycom_html(title, body)


def _polycom_status_list(title: str, rows: list[StatusRow]) -> str:
    lines = [f"<b>{_esc(title)}</b><br/>"]
    for row in rows:
        if row.dial_uri:
            lines.append(
                f'<a href="{_esc(row.dial_uri)}">{_esc(row.label)}: {_esc(row.value)}</a><br/>'
            )
        else:
            lines.append(f"{_esc(row.label)}: {_esc(row.value)}<br/>")
    return _polycom_html(title, "\n".join(lines))
