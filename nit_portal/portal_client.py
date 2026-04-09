from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime

import requests
from bs4 import BeautifulSoup, Tag


BASE_URL = "https://portal.nit.ac.jp"
LOGIN_URL = f"{BASE_URL}/uprx/up/pk/pky001/Pky00101.xhtml"
MENU_URL = f"{BASE_URL}/uprx/up/bs/bsc005/Bsc00501.xhtml"
NOTICE_URL = f"{BASE_URL}/uprx/up/bs/bsd007/Bsd00701.xhtml"
STUDENT_TIMETABLE_MENUID = "1_0_0_2"
NOTICE_MENUID = "0_2_0_0"
WEEKDAYS = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日"]
NOTICE_TAB_LABELS = {
    0: "group",
    1: "all",
    2: "class",
    3: "schedule_change",
    4: "read",
    5: "unread",
    6: "new",
    7: "important",
    8: "application",
    9: "flagged",
}


@dataclass
class TimetableClass:
    period: str
    weekday: str
    subject: str
    instructor: str
    room: str
    course_code: str
    credits: str
    note: str


@dataclass
class TimetablePayload:
    title: str
    year: int
    semester: str
    campus: str
    campus_periods: str
    classes: list[TimetableClass]


@dataclass
class NoticeSummary:
    portal_notice_key: str
    title: str
    sender: str
    published_on: date | None
    is_new: bool
    is_important: bool
    is_flagged: bool
    is_read: bool
    source_tab_labels: list[str]
    detail_link_ids: list[str]


@dataclass
class NoticeDetail:
    category: str | None
    body: str | None
    notice_starts_at: datetime | None
    notice_ends_at: datetime | None


@dataclass
class NoticePayload:
    title: str
    notices: list[dict]


def get_text(tag: Tag | None) -> str:
    if tag is None:
        return ""
    return " ".join(tag.get_text(" ", strip=True).split())


def normalize_whitespace(value: str) -> str:
    return " ".join(value.split())


def make_notice_summary_key(title: str, sender: str, published_on: date | None) -> str:
    published = published_on.isoformat() if published_on else ""
    digest = hashlib.sha256(f"{title}|{sender}|{published}".encode("utf-8")).hexdigest()
    return digest[:40]


def make_notice_key(payload: dict) -> str:
    raw = "|".join(
        [
            payload.get("title") or "",
            payload.get("sender") or "",
            payload.get("published_on") or "",
            payload.get("category") or "",
            payload.get("body") or "",
            payload.get("notice_starts_at") or "",
            payload.get("notice_ends_at") or "",
        ]
    )
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return digest[:40]


def make_timetable_key(year: int, semester: str, campus: str, entry: TimetableClass) -> str:
    raw = "|".join(
        [
            str(year),
            semester,
            campus,
            entry.weekday,
            entry.period,
            entry.subject,
            entry.instructor,
            entry.course_code,
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:40]


def parse_notice_tab_label(detail_link_id: str) -> str | None:
    match = re.match(r"funcForm:tabArea:(\d+):", detail_link_id)
    if not match:
        return None
    return NOTICE_TAB_LABELS.get(int(match.group(1)), f"tab_{match.group(1)}")


def make_notice_content_hash(payload: dict) -> str:
    normalized = {
        "title": payload.get("title") or "",
        "sender": payload.get("sender") or "",
        "published_on": payload.get("published_on") or "",
        "category": payload.get("category") or "",
        "body": payload.get("body") or "",
        "notice_starts_at": payload.get("notice_starts_at") or "",
        "notice_ends_at": payload.get("notice_ends_at") or "",
        "is_new": bool(payload.get("is_new")),
        "is_important": bool(payload.get("is_important")),
        "is_flagged": bool(payload.get("is_flagged")),
        "is_read": bool(payload.get("is_read")),
        "source_tab_labels": list(payload.get("source_tab_labels") or []),
        "detail_link_ids": list(payload.get("detail_link_ids") or []),
    }
    return hashlib.sha256(json.dumps(normalized, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


class PortalClient:
    def __init__(self, user_name: str, password: str) -> None:
        self.user_name = user_name
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0"})

    def login(self) -> BeautifulSoup:
        self.session.get(f"{BASE_URL}/uprx/", timeout=20).raise_for_status()
        response = self.session.post(
            LOGIN_URL,
            data={
                "loginForm": "loginForm",
                "loginForm:userId": self.user_name,
                "loginForm:password": self.password,
                "loginForm:loginButton": "loginForm:loginButton",
                "javax.faces.ViewState": "stateless",
            },
            timeout=20,
        )
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")

    def _menu_transition(self, portal_home: BeautifulSoup, menuid: str) -> BeautifulSoup:
        menu_form = portal_home.find("form", id="menuForm")
        if menu_form is None:
            raise RuntimeError("menuForm not found after login")

        payload = {
            field["name"]: field.get("value", "")
            for field in menu_form.select("input[name]")
        }
        payload.update(
            {
                "menuForm": "menuForm",
                "menuForm:mainMenu": "menuForm:mainMenu",
                "menuForm:mainMenu_menuid": menuid,
            }
        )
        response = self.session.post(MENU_URL, data=payload, timeout=20)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")

    def _expand_all_notices(self, board_page: BeautifulSoup) -> BeautifulSoup:
        func_form = board_page.find("form", id="funcForm")
        if func_form is None:
            raise RuntimeError("funcForm not found on notice page")

        initial_payload = {
            field["name"]: field.get("value", "")
            for field in func_form.select("input[name], select[name]")
        }
        tab_payload = dict(initial_payload)
        tab_payload.update(
            {
                "funcForm": "funcForm",
                "javax.faces.partial.ajax": "true",
                "javax.faces.source": "funcForm:tabArea",
                "javax.faces.partial.execute": "funcForm:tabArea",
                "javax.faces.partial.render": "funcForm:tabArea",
                "javax.faces.behavior.event": "tabChange",
                "javax.faces.partial.event": "tabChange",
                "funcForm:tabArea_activeIndex": "1",
                "funcForm:tabArea_tabindex": "1",
            }
        )
        tab_response = self.session.post(
            NOTICE_URL,
            data=tab_payload,
            headers={"Faces-Request": "partial/ajax"},
            timeout=20,
        )
        tab_response.raise_for_status()

        tab_response_text = tab_response.text
        all_payload = dict(initial_payload)
        all_payload["funcForm"] = "funcForm"
        all_payload["funcForm:tabArea_activeIndex"] = "1"
        if view_state := self._extract_partial_update(tab_response_text, "j_id1:javax.faces.ViewState:0"):
            all_payload["javax.faces.ViewState"] = view_state
        for token_name in ("rx-token", "rx-loginKey", "rx-deviceKbn", "rx-loginType"):
            token_match = re.search(rf'name="{re.escape(token_name)}" value="([^"]+)"', tab_response_text)
            if token_match:
                all_payload[token_name] = token_match.group(1)
        all_payload.update(
            {
                "javax.faces.partial.ajax": "true",
                "javax.faces.source": "funcForm:tabArea:1:j_idt414",
                "javax.faces.partial.execute": "funcForm:tabArea:1:j_idt414",
                "javax.faces.partial.render": "funcForm",
                "funcForm:tabArea:1:j_idt414": "funcForm:tabArea:1:j_idt414",
            }
        )
        all_response = self.session.post(
            NOTICE_URL,
            data=all_payload,
            headers={"Faces-Request": "partial/ajax"},
            timeout=20,
        )
        all_response.raise_for_status()
        html = self._extract_partial_update(all_response.text, "funcForm") or self._extract_html_payload(all_response.text)
        return BeautifulSoup(html, "html.parser")

    def fetch_timetable(self, portal_home: BeautifulSoup | None = None) -> TimetablePayload:
        home = portal_home or self.login()
        page = self._menu_transition(home, STUDENT_TIMETABLE_MENUID)
        func_form = page.find("form", id="funcForm")
        if func_form is None:
            raise RuntimeError("funcForm not found on timetable page")

        year_input = func_form.find("input", {"name": "funcForm:nendo_input"})
        semester_select = func_form.find("select", {"name": "funcForm:gakki_input"})
        campus_select = func_form.find("select", {"name": "funcForm:campusNo_input"})
        campus_periods = page.find(string=lambda s: isinstance(s, str) and "埼玉キャンパス（1限" in s)

        semester = get_text(semester_select.find("option", selected=True) if semester_select else None)
        campus = get_text(campus_select.find("option", selected=True) if campus_select else None)
        if not campus and campus_select is not None:
            choices = [get_text(option) for option in campus_select.find_all("option") if option.get("value")]
            if len(choices) == 1:
                campus = choices[0]

        classes = self._parse_timetable_entries(page)

        return TimetablePayload(
            title=get_text(page.select_one("#breadCrumbArea h2")),
            year=int(year_input.get("value", "0")) if year_input else 0,
            semester=semester,
            campus=campus,
            campus_periods=normalize_whitespace(campus_periods) if campus_periods else "",
            classes=classes,
        )

    def _parse_timetable_entries(self, page: BeautifulSoup) -> list[TimetableClass]:
        table = None
        for candidate in page.find_all("table"):
            header_text = get_text(candidate.find("thead"))
            if all(day in header_text for day in WEEKDAYS[:5]):
                table = candidate
                break

        if table is None:
            raise RuntimeError("timetable table not found")

        entries: list[TimetableClass] = []
        body_rows = table.find("tbody")
        if body_rows is None:
            return entries

        for row in body_rows.find_all("tr", recursive=False):
            period_cell = row.find("td", class_="colJigen")
            period = get_text(period_cell)
            if not period or period == "昼休み":
                continue

            cells = row.find_all("td", class_="colYobi", recursive=False)
            for weekday, cell in zip(WEEKDAYS, cells):
                class_box = cell.find("div", class_="jugyo-info")
                if class_box is None or "noClass" in class_box.get("class", []):
                    continue

                top_level_divs = class_box.find_all("div", recursive=False)
                entries.append(
                    TimetableClass(
                        period=period,
                        weekday=weekday,
                        subject=get_text(class_box.find("div", class_="fontB")),
                        instructor=get_text(top_level_divs[1]) if len(top_level_divs) > 1 else "",
                        room=get_text(top_level_divs[2]) if len(top_level_divs) > 2 else "",
                        course_code=get_text(top_level_divs[3]) if len(top_level_divs) > 3 else "",
                        credits=get_text(class_box.find("div", class_="taniSu")),
                        note=get_text(class_box.find("div", class_="sign")),
                    )
                )

        return entries

    def fetch_notice_summaries(self, board_page: BeautifulSoup | None = None) -> tuple[str, list[NoticeSummary]]:
        seed_page = board_page or self._menu_transition(self.login(), NOTICE_MENUID)
        expanded_page = self._expand_all_notices(seed_page)
        title = get_text((expanded_page if expanded_page else seed_page).select_one("#breadCrumbArea h2"))
        summaries: list[NoticeSummary] = []
        for page in (seed_page, expanded_page):
            self._collect_notice_summaries(page, summaries)
        return title, summaries

    def _collect_notice_summaries(self, page: BeautifulSoup, summaries: list[NoticeSummary]) -> None:
        func_form = page.find("form", id="funcForm")
        if func_form is None:
            raise RuntimeError("funcForm not found on notice page")
        for link in func_form.find_all("a", id=True):
            link_id = link.get("id", "")
            if not any(token in link_id for token in (":j_idt301", ":j_idt384")):
                continue

            container = link.find_parent("div", class_="alignRight")
            if container is None:
                continue

            info_block = container.find("dl")
            if info_block is None:
                continue

            trailing_text = " ".join(
                text.strip()
                for text in info_block.find_all(string=True, recursive=False)
                if text.strip()
            )
            match = re.search(r"\[(.*?)\]\s+(\d{4}/\d{2}/\d{2})$", trailing_text)
            sender = match.group(1) if match else ""
            published_on = datetime.strptime(match.group(2), "%Y/%m/%d").date() if match else None

            icon_classes = [set(icon.get("class", [])) for icon in info_block.find_all("i")]
            is_important = any("iconColorAttention" in classes and "hiddenStyle" not in classes for classes in icon_classes)
            is_new = any("iconColorNew" in classes and "hiddenStyle" not in classes for classes in icon_classes)

            flag_input = container.find("input", id=lambda value: value and value.endswith("401_input"))
            read_input = container.find("input", id=lambda value: value and value.endswith("402_input"))

            title = get_text(link)
            candidate = NoticeSummary(
                portal_notice_key="",
                title=title,
                sender=sender,
                published_on=published_on,
                is_new=is_new,
                is_important=is_important,
                is_flagged=bool(flag_input and flag_input.has_attr("checked")),
                is_read=bool(read_input and read_input.has_attr("checked")),
                source_tab_labels=[label] if (label := parse_notice_tab_label(link_id)) else [],
                detail_link_ids=[link_id],
            )
            summaries.append(candidate)

    def fetch_notice_detail(self, board_page: BeautifulSoup, detail_link_ids: list[str]) -> NoticeDetail:
        func_form = board_page.find("form", id="funcForm")
        if func_form is None:
            raise RuntimeError("funcForm not found on notice page")

        dialog = None
        for detail_link_id in detail_link_ids:
            payload = {
                field["name"]: field.get("value", "")
                for field in func_form.select("input[name], select[name]")
            }
            payload.update(
                {
                    "funcForm": "funcForm",
                    "javax.faces.partial.ajax": "true",
                    "javax.faces.source": detail_link_id,
                    "javax.faces.partial.execute": detail_link_id,
                    "javax.faces.partial.render": "@all",
                    detail_link_id: detail_link_id,
                }
            )
            response = self.session.post(
                NOTICE_URL,
                data=payload,
                headers={"Faces-Request": "partial/ajax"},
                timeout=20,
            )
            response.raise_for_status()

            html = self._extract_html_payload(response.text)
            dialog = BeautifulSoup(html, "html.parser").find(id="bsd00702:dialog")
            if dialog is not None:
                break

        if dialog is None:
            return NoticeDetail(category=None, body=None, notice_starts_at=None, notice_ends_at=None)

        cells = dialog.find_all("td")
        details: dict[str, str] = {}
        for index in range(0, len(cells) - 1, 2):
            key = get_text(cells[index])
            value = get_text(cells[index + 1])
            if key:
                details[key] = value

        period_raw = details.get("掲示期間", "")
        starts_at, ends_at = self._parse_notice_period(period_raw)

        return NoticeDetail(
            category=details.get("カテゴリ") or None,
            body=details.get("本文") or None,
            notice_starts_at=starts_at,
            notice_ends_at=ends_at,
        )

    def _fetch_notice_detail_isolated(self, detail_link_ids: list[str]) -> NoticeDetail:
        for detail_link_id in detail_link_ids:
            if detail_link_id.startswith("funcForm:tabArea:0:"):
                board_page = self._menu_transition(self.login(), NOTICE_MENUID)
            else:
                seed_page = self._menu_transition(self.login(), NOTICE_MENUID)
                board_page = self._expand_all_notices(seed_page)

            detail = self.fetch_notice_detail(board_page, [detail_link_id])
            if detail.body or detail.category or detail.notice_starts_at or detail.notice_ends_at:
                return detail

        return NoticeDetail(category=None, body=None, notice_starts_at=None, notice_ends_at=None)

    def _extract_html_payload(self, response_text: str) -> str:
        match = re.search(r'<update id="javax\.faces\.ViewRoot"><!\[CDATA\[(.*)\]\]></update>', response_text, re.S)
        if match:
            return match.group(1)
        return response_text

    def _extract_partial_update(self, response_text: str, update_id: str) -> str | None:
        match = re.search(rf'<update id="{re.escape(update_id)}"><!\[CDATA\[(.*?)\]\]></update>', response_text, re.S)
        if match:
            return match.group(1)
        return None

    def _parse_notice_period(self, value: str) -> tuple[datetime | None, datetime | None]:
        match = re.search(
            r"(\d{4}/\d{2}/\d{2})\([^)]+\)\s+(\d{2}:\d{2})\s+～\s+(\d{4}/\d{2}/\d{2})\([^)]+\)\s+(\d{2}:\d{2})",
            value,
        )
        if not match:
            return None, None
        start = datetime.strptime(f"{match.group(1)} {match.group(2)}", "%Y/%m/%d %H:%M")
        end = datetime.strptime(f"{match.group(3)} {match.group(4)}", "%Y/%m/%d %H:%M")
        return start, end

    def fetch_notices(self, portal_home: BeautifulSoup | None = None) -> NoticePayload:
        home = portal_home or self.login()
        summary_page = self._menu_transition(home, NOTICE_MENUID)
        title, summaries = self.fetch_notice_summaries(summary_page)

        notices_by_key: dict[str, dict] = {}
        for summary in summaries:
            detail = self._fetch_notice_detail_isolated(summary.detail_link_ids)
            record = asdict(summary)
            record.update(asdict(detail))
            record["published_on"] = summary.published_on.isoformat() if summary.published_on else None
            record["notice_starts_at"] = detail.notice_starts_at.isoformat() if detail.notice_starts_at else None
            record["notice_ends_at"] = detail.notice_ends_at.isoformat() if detail.notice_ends_at else None
            record["portal_notice_key"] = make_notice_key(record)

            existing = notices_by_key.get(record["portal_notice_key"])
            if existing is None:
                record["content_hash"] = make_notice_content_hash(record)
                notices_by_key[record["portal_notice_key"]] = record
                continue

            existing["is_new"] = existing["is_new"] or record["is_new"]
            existing["is_important"] = existing["is_important"] or record["is_important"]
            existing["is_flagged"] = existing["is_flagged"] or record["is_flagged"]
            existing["is_read"] = existing["is_read"] or record["is_read"]
            for source_tab_label in record["source_tab_labels"]:
                if source_tab_label not in existing["source_tab_labels"]:
                    existing["source_tab_labels"].append(source_tab_label)
            for detail_link_id in record["detail_link_ids"]:
                if detail_link_id not in existing["detail_link_ids"]:
                    if detail_link_id.endswith("j_idt301"):
                        existing["detail_link_ids"].insert(0, detail_link_id)
                    else:
                        existing["detail_link_ids"].append(detail_link_id)
            existing["content_hash"] = make_notice_content_hash(existing)

        notices = list(notices_by_key.values())
        notices.sort(key=lambda item: (item["published_on"] or "", item["title"]), reverse=True)
        return NoticePayload(title=title, notices=notices)
