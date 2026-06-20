from __future__ import annotations

import base64
import html
import re
import time
from typing import Any
from urllib.parse import quote, urlencode

import httpx

from apps.legal_research.services.sources.weike.types import WeikeSearchItem, WeikeSession
from apps.legal_research.services.task.event_service import LegalResearchTaskEventService

class PrivateWeikeApiAdapter:
    def open_http_session(
        self,
        *,
        client: Any,
        username: str,
        password: str,
        login_url: str | None,
    ) -> WeikeSession:
        http_client = httpx.Client(
            follow_redirects=True,
            timeout=30.0,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
                )
            },
        )

        try:
            http_client.get(login_url or client.LOGIN_URL)
            http_client.post(
                client.HOME_LOGIN_URL,
                data={
                    "username": self._encode_login_field(username),
                    "password": self._encode_login_field(password),
                    "type": "h5",
                },
            )
            home_resp = http_client.get(client.HOME_URL)
            law_form_payload = self._extract_law_form_payload(home_resp.text)
            if not law_form_payload:
                raise RuntimeError("wk主页未获取到 law SSO 表单")

            http_client.post(client.LAW_SSO_URL, data=law_form_payload)
            law_list_resp = http_client.get(client.LAW_LIST_URL)
            if law_list_resp.status_code != 200:
                raise RuntimeError(f"wk API登录后访问列表失败: HTTP {law_list_resp.status_code}")
            if "抱歉，此功能需要登录后操作" in law_list_resp.text:
                raise RuntimeError("wk API登录失败：账号未进入已登录状态")

            return WeikeSession(
                http_client=http_client,
                username=username,
                password=password,
                login_url=login_url,
                search_via_api_enabled=True,
            )
        except Exception:
            http_client.close()
            raise

    def search_cases_via_api(
        self,
        *,
        client: Any,
        session: WeikeSession,
        keyword: str,
        max_candidates: int,
        max_pages: int,
        offset: int = 0,
        advanced_query: list[dict[str, str]] | None = None,
        court_filter: str = "",
        cause_of_action_filter: str = "",
        date_from: str = "",
        date_to: str = "",
        raw_payload: dict[str, Any] | None = None,
    ) -> list[WeikeSearchItem]:
        http_client = session.http_client
        if http_client is None:
            raise RuntimeError("私有wk API会话缺少http_client")

        items: list[WeikeSearchItem] = []
        seen: set[str] = set()
        request_offset = max(0, int(offset))
        remaining = max(1, int(max_candidates))
        session.last_search_doc_count = 0

        for _ in range(max_pages):
            page_size = max(1, min(50, remaining))
            if raw_payload is not None:
                payload = self._build_payload_from_raw(raw_payload, limit=page_size, offset=request_offset)
            else:
                payload = self._build_case_search_payload(
                    keyword=keyword,
                    limit=page_size,
                    offset=request_offset,
                    advanced_query=advanced_query,
                    court_filter=court_filter,
                    cause_of_action_filter=cause_of_action_filter,
                    date_from=date_from,
                    date_to=date_to,
                )
            url = "https://law.wkinfo.com.cn/csi/search"
            started = time.monotonic()
            data: dict[str, Any] | None = None
            status_code = 0

            try:
                resp = http_client.post(
                    url,
                    json=payload,
                    timeout=60.0,
                )
                status_code = int(resp.status_code)
                if status_code != 200:
                    self._record_search_event(
                        session=session,
                        keyword=keyword,
                        offset=request_offset,
                        limit=page_size,
                        request_payload=payload,
                        status_code=status_code,
                        duration_ms=int((time.monotonic() - started) * 1000),
                        success=False,
                        error_code=f"HTTP_{status_code}",
                        error_message=f"wk API检索失败: HTTP {status_code}",
                        response_summary={"status_code": status_code},
                    )
                    raise RuntimeError(f"wk API检索失败: HTTP {status_code}")

                payload_obj = resp.json()
                if not isinstance(payload_obj, dict):
                    self._record_search_event(
                        session=session,
                        keyword=keyword,
                        offset=request_offset,
                        limit=page_size,
                        request_payload=payload,
                        status_code=status_code,
                        duration_ms=int((time.monotonic() - started) * 1000),
                        success=False,
                        error_code="INVALID_JSON",
                        error_message="wk API检索返回非JSON对象",
                        response_summary={"payload_type": str(type(payload_obj))},
                    )
                    break
                data = payload_obj
            except RuntimeError:
                raise
            except Exception as exc:
                self._record_search_event(
                    session=session,
                    keyword=keyword,
                    offset=request_offset,
                    limit=page_size,
                    request_payload=payload,
                    status_code=status_code or None,
                    duration_ms=int((time.monotonic() - started) * 1000),
                    success=False,
                    error_code="REQUEST_ERROR",
                    error_message=str(exc),
                    response_summary={},
                )
                raise

            if not isinstance(data, dict):
                break

            metadata = data.get("searchMetadata") or {}
            search_id = str(metadata.get("searchId") or "")
            docs = data.get("documentList") or []
            total_hit_raw = metadata.get("docCount")
            total_hit_value: int | None
            try:
                total_hit_value = int(str(total_hit_raw))
            except (TypeError, ValueError):
                total_hit_value = None

            session.last_search_doc_count = max(0, total_hit_value or 0)

            response_summary = {
                "searchId": search_id,
                "docCount": session.last_search_doc_count,
                "returned_count": len(docs) if isinstance(docs, list) else 0,
                "offset": request_offset,
                "sample_doc_ids": (
                    [str((doc or {}).get("docId") or "") for doc in docs[:3] if isinstance(doc, dict)]
                    if isinstance(docs, list)
                    else []
                ),
            }
            self._record_search_event(
                session=session,
                keyword=keyword,
                offset=request_offset,
                limit=page_size,
                request_payload=payload,
                status_code=status_code,
                duration_ms=int((time.monotonic() - started) * 1000),
                success=True,
                response_summary=response_summary,
            )

            if not isinstance(docs, list) or not docs:
                break

            for doc in docs:
                if not isinstance(doc, dict):
                    continue

                doc_id_unquoted = str(doc.get("docId") or "").strip()
                if not doc_id_unquoted:
                    continue

                doc_id_raw = quote(doc_id_unquoted, safe="")
                if doc_id_unquoted in seen or doc_id_raw in seen:
                    continue

                seen.add(doc_id_unquoted)
                seen.add(doc_id_raw)
                ordinal = str(doc.get("docOrdinal") or (len(items) + 1))
                query = {
                    "searchId": search_id,
                    "index": ordinal,
                    "q": keyword,
                    "module": "",
                    "childModule": "all",
                }
                detail_url = f"https://law.wkinfo.com.cn/judgment-documents/detail/{doc_id_raw}?{urlencode(query)}"

                items.append(
                    WeikeSearchItem(
                        doc_id_raw=doc_id_raw,
                        doc_id_unquoted=doc_id_unquoted,
                        detail_url=detail_url,
                        title_hint=self._html_to_text(str(doc.get("title") or "")),
                        search_id=search_id,
                        module="",
                    )
                )
                if len(items) >= max_candidates:
                    return items

            request_offset += len(docs)
            remaining = max(0, max_candidates - len(items))
            if total_hit_value is not None and total_hit_value <= request_offset:
                break

            if remaining <= 0:
                break
            if len(docs) < page_size:
                break

        return items

    @staticmethod
    def _record_search_event(
        *,
        session: WeikeSession,
        keyword: str,
        offset: int,
        limit: int,
        request_payload: dict[str, Any],
        status_code: int | None,
        duration_ms: int,
        success: bool,
        response_summary: object,
        error_code: str = "",
        error_message: str = "",
    ) -> None:
        LegalResearchTaskEventService.record_event(
            task_id=getattr(session, "task_id", ""),
            stage="search",
            source="api",
            interface_name="csi_search",
            method="POST",
            url="https://law.wkinfo.com.cn/csi/search",
            status_code=status_code,
            duration_ms=duration_ms,
            success=success,
            error_code=error_code,
            error_message=error_message,
            request_summary={
                "keyword": keyword,
                "offset": offset,
                "limit": limit,
                "payload": request_payload,
            },
            response_summary=response_summary,
        )

    @staticmethod
    def _build_payload_from_raw(
        raw_payload: dict[str, Any],
        *,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        """Clone a raw WKInfo payload and override pagination fields."""
        import copy

        payload = copy.deepcopy(raw_payload)
        page_info = payload.setdefault("pageInfo", {})
        page_info["limit"] = limit
        page_info["offset"] = offset
        return payload

    @staticmethod
    def _build_case_search_payload(
        *,
        keyword: str,
        limit: int,
        offset: int,
        advanced_query: list[dict[str, str]] | None = None,
        court_filter: str = "",
        cause_of_action_filter: str = "",
        date_from: str = "",
        date_to: str = "",
    ) -> dict[str, Any]:
        field_map = {
            "fullText": "fullText",
            "title": "title",
            "causeOfAction": "causeOfAction",
            "courtOpinion": "courtOpinion",
            "judgmentResult": "judgmentResult",
            "disputeFocus": "disputeFocus",
            "caseNumber": "caseNumber",
            "全文": "fullText",
            "标题": "title",
            "案由": "causeOfAction",
            "本院认为": "courtOpinion",
            "裁判结果": "judgmentResult",
            "争议焦点": "disputeFocus",
            "案号": "caseNumber",
            "本院查明": "causeFinding",
        }

        if advanced_query:
            parts: list[str] = []
            for i, item in enumerate(advanced_query):
                field = field_map.get(str(item.get("field", "") or ""), "fullText")
                kw = str(item.get("keyword", "") or "").strip()
                if not kw:
                    continue

                op = str(item.get("op", "AND") or "AND").upper()
                if op not in ("AND", "OR", "NOT"):
                    op = "AND"

                clause = f"{field}:(({kw}))"
                if i == 0:
                    parts.append(clause)
                else:
                    parts.append(f"{op} {clause}")
            query_string = " ".join(parts) if parts else f"simple:(({keyword}))"
        else:
            query_string = f"simple:(({keyword}))"

        # WK /csi/search API 的 filterQueries 仅支持 Solr 字符串格式（如 "-typeOfDecision:((008))"），
        # 不支持对象格式。法院/案由过滤由 DOM 检索路径处理，此处不放入 filterQueries。
        filter_queries: list[str] = []

        filter_dates: list[dict[str, Any]] = []
        if date_from or date_to:
            filter_dates.append(
                {
                    "field": "judgmentDate",
                    "from": date_from or "",
                    "to": date_to or "",
                }
            )

        return {
            "query": {
                "queryString": query_string,
                "filterDates": filter_dates,
                "filterQueries": filter_queries,
            },
            "searchScope": {"treeNodeIds": []},
            "relatedIndexQueries": [],
            "sortOrderList": [
                {"sortKey": "score", "sortDirection": "DESC"},
                {"sortKey": "judgmentDate", "sortDirection": "DESC"},
            ],
            "pageInfo": {"limit": limit, "offset": offset},
            "chargingInfo": {"useBalance": True},
            "otherOptions": {
                "requireLanguage": "cn",
                "relatedIndexEnabled": True,
                "groupEnabled": False,
                "smartEnabled": True,
                "buy": False,
                "summaryLengthLimit": 100,
                "synonymEnabled": True,
                "advanced": bool(advanced_query),
                "isHideBigLib": 0,
                "relatedIndexFetchRows": 5,
                "proximateCourtID": "",
                "module": "",
                "correctEnabled": True,
                "mappingEnabled": True,
                "webSearchEnabled": False,
                "defaultSearch": False,
            },
            "indexId": "law.case",
        }

    @staticmethod
    def _encode_login_field(value: str) -> str:
        encoded = quote(value, safe="~()*!.'")
        return base64.b64encode(encoded.encode("ascii")).decode("ascii")

    @staticmethod
    def _extract_law_form_payload(home_html: str) -> dict[str, str]:
        form_match = re.search(r'<form[^>]+id="laws"[\s\S]*?</form>', home_html)
        if not form_match:
            return {}

        form_html = form_match.group(0)

        def _pick(name: str) -> str:
            m = re.search(rf'name="{name}"\s+value="([^"]*)"', form_html)
            if not m:
                return ""
            return html.unescape(m.group(1))

        return {
            "username": _pick("username"),
            "password": _pick("password"),
            "ticket": _pick("ticket"),
        }

    @staticmethod
    def _html_to_text(html_content: str) -> str:
        text = re.sub(r"<script[\\s\\S]*?</script>", " ", html_content, flags=re.I)
        text = re.sub(r"<style[\\s\\S]*?</style>", " ", text, flags=re.I)
        text = re.sub(r"<br\\s*/?>", "\\n", text, flags=re.I)
        text = re.sub(r"</p>", "\\n", text, flags=re.I)
        text = re.sub(r"<[^>]+>", " ", text)
        text = html.unescape(text)
        text = re.sub(r"[\\t\\r ]+", " ", text)
        text = re.sub(r"\\n{3,}", "\\n\\n", text)
        return text.strip()

    # ──────────────────────────────────────────────────────────────
    # 法律法规检索 (law.legislation)
    # ──────────────────────────────────────────────────────────────

    def search_laws_via_api(
        self,
        *,
        session: WeikeSession,
        keyword: str,
        max_candidates: int = 5,
    ) -> list[dict[str, Any]]:
        """搜索法律法规，返回匹配的法规列表."""
        http_client = session.http_client
        if http_client is None:
            raise RuntimeError("私有wk API会话缺少http_client")

        payload = {
            "query": {
                "queryString": f"simple:(({keyword}))",
                "filterDates": [],
                "filterQueries": [],
            },
            "searchScope": {"treeNodeIds": []},
            "relatedIndexQueries": [],
            "sortOrderList": [{"sortKey": "score", "sortDirection": "DESC"}],
            "pageInfo": {"limit": max_candidates, "offset": 0},
            "chargingInfo": {"useBalance": True},
            "otherOptions": {
                "requireLanguage": "cn",
                "smartEnabled": True,
                "synonymEnabled": True,
                "correctEnabled": True,
                "mappingEnabled": True,
            },
            "indexId": "law.legislation",
        }

        resp = http_client.post("https://law.wkinfo.com.cn/csi/search", json=payload, timeout=30.0)
        if resp.status_code != 200:
            raise RuntimeError(f"威科法律法规检索失败: HTTP {resp.status_code}")

        data = resp.json()
        docs = data.get("documentList") or []
        results: list[dict[str, Any]] = []
        for doc in docs:
            if not isinstance(doc, dict):
                continue
            af = doc.get("additionalFields") or {}
            results.append({
                "docId": str(doc.get("docId") or ""),
                "title": self._html_to_text(str(doc.get("title") or "")),
                "validityStatus": str(af.get("validityStatus") or ""),
                "validityStatusText": str(af.get("validityStatusText") or ""),
                "promulgatingDate": str(af.get("promulgatingDate") or ""),
                "documentNumber": str(af.get("documentNumber") or ""),
                "promulgatingAgency": str(af.get("promulgatingAgencySummary") or ""),
            })
        return results

    def fetch_law_article_via_api(
        self,
        *,
        session: WeikeSession,
        doc_id: str,
        article_num: int,
    ) -> str | None:
        """获取法规的第N条条文原文."""
        http_client = session.http_client
        if http_client is None:
            raise RuntimeError("私有wk API会话缺少http_client")

        url = (
            f"https://law.wkinfo.com.cn/csi/document/{doc_id}/html"
            f"?indexId=law.legislation&print=false&fromType=&useBalance=true&module="
        )
        resp = http_client.get(url, timeout=60.0)
        if resp.status_code != 200:
            raise RuntimeError(f"威科法规详情获取失败: HTTP {resp.status_code}")

        return self._extract_article_from_html(resp.text, article_num)

    @staticmethod
    def _extract_article_from_html(html_text: str, article_num: int) -> str | None:
        """从法规 HTML 中提取第N条条文原文.

        跳过交叉引用（如 "第X条、第Y条的规定"），定位真正的条文标题。
        """
        chinese_num = _int_to_chinese(article_num)
        if not chinese_num:
            return None

        # 查找所有 "第X条" 出现位置
        pattern = re.compile(rf"第{chinese_num}条")
        matches = list(pattern.finditer(html_text))

        if not matches:
            ar_pattern = re.compile(rf"第{article_num}条")
            matches = list(ar_pattern.finditer(html_text))

        if not matches:
            return None

        # 跳过交叉引用：后面紧跟 "、" "的规定" 或 HTML 标签后跟 "第"
        for m in matches:
            after_raw = html_text[m.end(): m.end() + 200]
            after = re.sub(r"<[^>]+>", "", after_raw).lstrip()
            if re.match(r"^[、的规定第]", after):
                continue
            return _extract_article_text_from_position(html_text, m.start())

        return _extract_article_text_from_position(html_text, matches[-1].start())

API_ADAPTER = PrivateWeikeApiAdapter()


# ──────────────────────────────────────────────────────────────
# 模块级辅助函数
# ──────────────────────────────────────────────────────────────


def _extract_article_text_from_position(html_text: str, start: int) -> str:
    """从 HTML 中给定位置开始，提取当前条文的纯文本内容.

    用威科 HTML 中的锚点 _BxxxT{数字} 做条文边界切割。
    """
    remaining = html_text[start + 10:]
    next_anchor = re.search(r'<a\s+name=\\?"[^"]*T\d+\\?"[^>]*>', remaining)
    end = start + 10 + next_anchor.start() if next_anchor else len(html_text)

    p_start = html_text.rfind("<p", max(0, start - 500), start)
    if p_start < 0:
        p_start = max(0, start - 100)

    segment = html_text[p_start:end]
    text = re.sub(r"<[^>]+>", "", segment)
    text = html.unescape(text)
    text = re.sub(r"[ \t\r]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _int_to_chinese(num: int) -> str:
    """将阿拉伯数字转为中文数字（支持1-9999）."""
    if num <= 0 or num > 9999:
        return ""

    digits = "零一二三四五六七八九"
    units = ["", "十", "百", "千"]

    if num < 10:
        return digits[num]
    if num < 20:
        return "十" + (digits[num % 10] if num % 10 else "")
    if num < 100:
        tens, ones = divmod(num, 10)
        return digits[tens] + "十" + (digits[ones] if ones else "")
    if num < 1000:
        hundreds, rest = divmod(num, 100)
        tens, ones = divmod(rest, 10)
        result = digits[hundreds] + "百"
        if tens == 0 and ones:
            result += "零" + digits[ones]
        elif tens:
            result += digits[tens] + "十" + (digits[ones] if ones else "")
        return result

    thousands, rest = divmod(num, 1000)
    hundreds, rest = divmod(rest, 100)
    tens, ones = divmod(rest, 10)
    result = digits[thousands] + "千"
    if hundreds == 0 and (tens or ones):
        result += "零"
        if tens:
            result += digits[tens] + "十" + (digits[ones] if ones else "")
        else:
            result += digits[ones]
    elif hundreds:
        result += digits[hundreds] + "百"
        if tens == 0 and ones:
            result += "零" + digits[ones]
        elif tens:
            result += digits[tens] + "十" + (digits[ones] if ones else "")
    return result
