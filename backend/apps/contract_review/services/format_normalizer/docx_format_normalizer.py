"""合同格式规范化工具

将混乱格式的合同统一为标准格式：
- 页边距：A4 标准（上下 2.54cm，左右 3.17cm）
- 字号：正文 12 磅（小四号）
- 行距：1.5 倍行距（360 twips / auto）
- 段前间距：0
- 首行缩进：2 字符（480 twips）
- 编号：一、二、三...条 标准格式
"""

import logging
import re
from pathlib import Path
from typing import Any

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

logger = logging.getLogger(__name__)

# ============ 常量定义 ============

# 页边距（EMU 单位）
MARGIN_TOP = Cm(2.54)      # 1 英寸 = 2.54cm
MARGIN_BOTTOM = Cm(2.54)
MARGIN_LEFT = Cm(3.17)     # 标准 A4 左边距
MARGIN_RIGHT = Cm(3.17)

# 字号（半磅为单位）
FONT_SIZE_BODY = 24        # 12 磅 = 小四号
FONT_SIZE_TITLE = 52       # 26 磅 = 合同标题
FONT_SIZE_SUBTITLE = 32    # 16 磅 = 条标题

# 行距（twips，1 磅 = 20 twips）
LINE_SPACING = 360         # 1.5 倍行距
LINE_SPACING_EXACT = 400   # 固定 20 磅行距

# 段前间距
PARA_BEFORE = 0
PARA_AFTER = 0

# 首行缩进（twips）
FIRST_LINE_INDENT = 480    # 2 字符 ≈ 240 twips/字符

# 字体
FONT_CHINESE = "宋体"
FONT_ENGLISH = "Times New Roman"


class DocxFormatNormalizer:
    """合同格式规范化器"""

    def __init__(self, input_path: str | Path, output_path: str | Path | None = None):
        self.input_path = Path(input_path)
        self.output_path = Path(output_path) if output_path else self.input_path.parent / f"{self.input_path.stem}_规范化{self.input_path.suffix}"
        self.doc: Document | None = None

    def normalize(self) -> Path:
        """执行格式规范化，返回输出文件路径"""
        logger.info("开始规范化: %s", self.input_path)
        self.doc = Document(str(self.input_path))

        # 1. 设置页边距
        self._normalize_margins()

        # 2. 定义编号样式
        self._setup_numbering()

        # 3. 规范化段落格式
        self._normalize_paragraphs()

        # 4. 保存
        self.doc.save(str(self.output_path))
        logger.info("规范化完成: %s", self.output_path)
        return self.output_path

    def _normalize_margins(self) -> None:
        """统一页边距为 A4 标准"""
        for section in self.doc.sections:
            section.top_margin = MARGIN_TOP
            section.bottom_margin = MARGIN_BOTTOM
            section.left_margin = MARGIN_LEFT
            section.right_margin = MARGIN_RIGHT
        logger.debug("页边距已标准化")

    def _create_numbering_part(self) -> Any:
        """手动创建 numbering part，返回 XML element"""
        from docx.opc.constants import RELATIONSHIP_TYPE as RT
        from docx.opc.part import Part
        from docx.opc.packuri import PackURI
        from lxml import etree

        # 创建 numbering.xml 的 XML element（带命名空间）
        nsmap = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        numbering_elm = etree.SubElement(
            etree.Element('root'),
            qn('w:numbering'),
            nsmap=nsmap
        )

        # 序列化为 bytes
        numbering_xml = etree.tostring(numbering_elm, xml_declaration=True, encoding='UTF-8', standalone=True)

        # 创建 Part
        part_name = PackURI('/word/numbering.xml')
        content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml'
        numbering_part = Part(part_name, content_type, numbering_xml, self.doc.part.package)

        # 添加关系
        self.doc.part.relate_to(numbering_part, RT.NUMBERING)

        # 保存引用以便后续更新
        self._numbering_part = numbering_part

        return numbering_elm

    def _setup_numbering(self) -> None:
        """设置自动编号样式（一、二、三...条）"""
        # 尝试获取已有的 numbering part，如果没有则创建
        try:
            numbering_part = self.doc.part.numbering_part
            numbering_elm = numbering_part._element
        except (KeyError, NotImplementedError):
            # 文档没有 numbering part，需要手动创建
            numbering_elm = self._create_numbering_part()

        # 创建 abstractNum（抽象编号定义）- 匹配修订版格式
        abstractNum = OxmlElement('w:abstractNum')
        abstractNum.set(qn('w:abstractNumId'), '0')

        # 一级：一、二、三...（chineseCounting，后缀 nothing）
        lvl0 = OxmlElement('w:lvl')
        lvl0.set(qn('w:ilvl'), '0')
        lvl0.set(qn('w:tentative'), '0')
        lvl0.append(self._make_start('1'))
        lvl0.append(self._make_numFmt('chineseCounting'))
        lvl0.append(self._make_suff('nothing'))
        lvl0.append(self._make_lvlText('%1、'))
        lvl0.append(self._make_lvlJc('left'))
        pPr0 = OxmlElement('w:pPr')
        ind0 = OxmlElement('w:ind')
        ind0.set(qn('w:left'), '0')
        ind0.set(qn('w:firstLine'), '400')
        pPr0.append(ind0)
        lvl0.append(pPr0)
        abstractNum.append(lvl0)

        # 二级：1. 2. 3.（decimal，后缀 nothing）
        lvl1 = OxmlElement('w:lvl')
        lvl1.set(qn('w:ilvl'), '1')
        lvl1.set(qn('w:tentative'), '0')
        lvl1.append(self._make_start('1'))
        lvl1.append(self._make_numFmt('decimal'))
        lvl1.append(self._make_suff('nothing'))
        lvl1.append(self._make_lvlText('%2．'))
        lvl1.append(self._make_lvlJc('left'))
        pPr1 = OxmlElement('w:pPr')
        ind1 = OxmlElement('w:ind')
        ind1.set(qn('w:left'), '0')
        ind1.set(qn('w:firstLine'), '400')
        pPr1.append(ind1)
        lvl1.append(pPr1)
        abstractNum.append(lvl1)

        # 三级：（1）（2）（3）（decimal，后缀 nothing）
        lvl2 = OxmlElement('w:lvl')
        lvl2.set(qn('w:ilvl'), '2')
        lvl2.set(qn('w:tentative'), '0')
        lvl2.append(self._make_start('1'))
        lvl2.append(self._make_numFmt('decimal'))
        lvl2.append(self._make_suff('nothing'))
        lvl2.append(self._make_lvlText('（%3）'))
        lvl2.append(self._make_lvlJc('left'))
        pPr2 = OxmlElement('w:pPr')
        ind2 = OxmlElement('w:ind')
        ind2.set(qn('w:left'), '0')
        ind2.set(qn('w:firstLine'), '402')
        pPr2.append(ind2)
        lvl2.append(pPr2)
        abstractNum.append(lvl2)

        # 插入到 numbering 元素开头
        numbering_elm.insert(0, abstractNum)

        # 创建 num 实例（numId=1，引用 abstractNumId=0）
        num = OxmlElement('w:num')
        num.set(qn('w:numId'), '1')
        abstractNumRef = OxmlElement('w:abstractNumId')
        abstractNumRef.set(qn('w:val'), '0')
        num.append(abstractNumRef)
        numbering_elm.append(num)

        # 如果是新创建的 part，需要更新其内容
        if hasattr(self, '_numbering_part'):
            from lxml import etree
            self._numbering_part._blob = etree.tostring(numbering_elm, xml_declaration=True, encoding='UTF-8', standalone=True)

        logger.debug("编号样式已创建")

    def _make_start(self, val: str) -> OxmlElement:
        """创建 start 元素"""
        el = OxmlElement('w:start')
        el.set(qn('w:val'), val)
        return el

    def _make_numFmt(self, val: str) -> OxmlElement:
        """创建 numFmt 元素"""
        el = OxmlElement('w:numFmt')
        el.set(qn('w:val'), val)
        return el

    def _make_suff(self, val: str) -> OxmlElement:
        """创建 suff 元素"""
        el = OxmlElement('w:suff')
        el.set(qn('w:val'), val)
        return el

    def _make_lvlText(self, val: str) -> OxmlElement:
        """创建 lvlText 元素"""
        el = OxmlElement('w:lvlText')
        el.set(qn('w:val'), val)
        return el

    def _make_lvlJc(self, val: str) -> OxmlElement:
        """创建 lvlJc 元素"""
        el = OxmlElement('w:lvlJc')
        el.set(qn('w:val'), val)
        return el

        lvlText = OxmlElement('w:lvlText')
        lvlText.set(qn('w:val'), level_text)
        lvl.append(lvlText)

        lvlJc = OxmlElement('w:lvlJc')
        lvlJc.set(qn('w:val'), 'left')
        lvl.append(lvlJc)

        # 缩进设置
        pPr = OxmlElement('w:pPr')
        ind = OxmlElement('w:ind')
        ind.set(qn('w:left'), left)
        ind.set(qn('w:hanging'), hanging)
        pPr.append(ind)
        lvl.append(pPr)

        return lvl

    def _normalize_paragraphs(self) -> None:
        """规范化所有段落格式"""
        for para in self.doc.paragraphs:
            # 判断段落类型并应用对应格式
            para_type = self._classify_paragraph(para)
            self._apply_paragraph_format(para, para_type)

            # 如果是空行，清除 run 上的属性
            if para_type == 'empty':
                self._clear_run_properties(para)

        logger.debug("段落格式已规范化")

    def _clear_run_properties(self, para: Any) -> None:
        """清除段落中所有 run 的属性"""
        for run in para.runs:
            rPr = run._element.find(qn('w:rPr'))
            if rPr is not None:
                run._element.remove(rPr)

    def _classify_paragraph(self, para: Any) -> str:
        """分类段落类型"""
        text = para.text.strip()

        # 空行
        if not text:
            return 'empty'

        # 标题（合同标题）
        if self._is_contract_title(text):
            return 'title'

        # 甲方/乙方行（两端对齐）
        if self._is_party_header(text):
            return 'party_header'

        # 当事人详细信息（法定代表人、地址、信用代码等）
        if self._is_party_detail(text):
            return 'party_detail'

        # 条标题（第一条、第二条...）- 转换为编号样式
        if self._is_article_title(text):
            return 'article_title'

        # 款标题（（一）、（二）...）
        if self._is_clause_title(text):
            return 'clause_title'

        # 项标题（1. 2. 3....）
        if self._is_item_title(text):
            return 'item_title'

        # 默认为正文
        return 'body'

    def _is_contract_title(self, text: str) -> bool:
        """判断是否为合同标题"""
        title_keywords = ['合同', '协议', '契约', '合约']
        return any(kw in text for kw in title_keywords) and len(text) < 30

    def _is_party_header(self, text: str) -> bool:
        """判断是否为甲方/乙方行（两端对齐）"""
        return bool(re.match(r'^[甲乙丙丁]方[：:]', text))

    def _is_party_detail(self, text: str) -> bool:
        """判断是否为当事人详细信息（左对齐）"""
        detail_patterns = [
            r'^法定代表人[：:]',
            r'^地址[：:]',
            r'^统一社会信用代码[：:]',
            r'^联系人[/／]电话',
            r'^电话[：:]',
            r'^法人[：:]',
        ]
        return any(re.match(p, text) for p in detail_patterns)

    def _is_party_b_detail(self, text: str) -> bool:
        """判断是否为乙方详细信息（需要加粗）"""
        # 乙方的法定代表人、地址、信用代码等需要加粗
        if not self._is_party_detail(text):
            return False
        # 检查前面是否有乙方行
        return True  # 简化处理，所有详细信息都加粗

    def _is_article_title(self, text: str) -> bool:
        """判断是否为条标题（第X条）"""
        return bool(re.match(r'^第[一二三四五六七八九十百]+条', text))

    def _is_clause_title(self, text: str) -> bool:
        """判断是否为款标题（（X））"""
        return bool(re.match(r'^（[一二三四五六七八九十]+）', text))

    def _is_item_title(self, text: str) -> bool:
        """判断是否为项标题（X.）"""
        return bool(re.match(r'^\d+[.、]', text))

    def _apply_paragraph_format(self, para: Any, para_type: str) -> None:
        """应用段落格式"""
        pPr = para._element.get_or_add_pPr()

        # 清除旧的格式（包括编号）
        self._clear_old_format(pPr)

        # 根据类型设置格式
        if para_type == 'empty':
            self._apply_empty_format(pPr)
        elif para_type == 'title':
            self._apply_title_format(para, pPr)
        elif para_type == 'party_header':
            self._apply_party_header_format(para, pPr)
        elif para_type == 'party_detail':
            self._apply_party_detail_format(para, pPr)
        elif para_type == 'article_title':
            self._apply_article_title_format(para, pPr)
        elif para_type == 'clause_title':
            self._apply_clause_title_format(para, pPr)
        elif para_type == 'item_title':
            self._apply_item_title_format(para, pPr)
        else:  # body
            self._apply_body_format(para, pPr)

        # 非空行确保有对齐方式（默认 left）
        if para_type != 'empty' and pPr.find(qn('w:jc')) is None:
            self._set_alignment(pPr, 'left')

    def _clear_old_format(self, pPr: Any) -> None:
        """清除旧的格式定义"""
        # 清除 spacing、ind、jc、numPr
        for tag in ['w:spacing', 'w:ind', 'w:jc', 'w:numPr']:
            old = pPr.find(qn(tag))
            if old is not None:
                pPr.remove(old)

    def _apply_empty_format(self, pPr: Any) -> None:
        """空行格式：行距 1.5 倍，左缩进 0"""
        self._set_spacing(pPr)
        self._set_indent(pPr, left='0')
        # 清除空行 run 上的字号属性

    def _apply_title_format(self, para: Any, pPr: Any) -> None:
        """合同标题格式：居中、26磅、加粗"""
        self._set_alignment(pPr, 'center')
        self._set_spacing(pPr)
        self._set_indent(pPr, left='0')
        self._set_run_font(para, FONT_SIZE_TITLE, bold=True)

    def _apply_party_header_format(self, para: Any, pPr: Any) -> None:
        """甲方/乙方行格式：两端对齐、12磅"""
        self._set_alignment(pPr, 'both')
        self._set_spacing(pPr)
        self._set_indent(pPr, left='0')
        self._set_run_font(para, FONT_SIZE_BODY, bold=False)

    def _apply_party_detail_format(self, para: Any, pPr: Any) -> None:
        """当事人详细信息格式：左对齐、12磅"""
        self._set_alignment(pPr, 'left')
        self._set_spacing(pPr)
        self._set_indent(pPr, left='0')
        self._set_run_font(para, FONT_SIZE_BODY, bold=False)

    def _apply_article_title_format(self, para: Any, pPr: Any) -> None:
        """条标题格式：编号 lvl=1、12磅（因为文字中已包含"第一条"）"""
        self._set_spacing(pPr)
        self._set_indent(pPr, left='0')
        self._set_numbering(pPr, num_id='1', ilvl='1')
        self._set_run_font(para, FONT_SIZE_BODY, bold=False)

    def _apply_clause_title_format(self, para: Any, pPr: Any) -> None:
        """款标题格式：编号 lvl=1、12磅"""
        self._set_spacing(pPr)
        self._set_indent(pPr, left='0')
        self._set_numbering(pPr, num_id='1', ilvl='1')
        self._set_run_font(para, FONT_SIZE_BODY, bold=False)

    def _apply_item_title_format(self, para: Any, pPr: Any) -> None:
        """项标题格式：编号 lvl=2、12磅"""
        self._set_spacing(pPr)
        self._set_indent(pPr, left='0')
        self._set_numbering(pPr, num_id='1', ilvl='2')
        self._set_run_font(para, FONT_SIZE_BODY, bold=False)

    def _apply_body_format(self, para: Any, pPr: Any) -> None:
        """正文格式：12磅、左缩进 0"""
        # 不设置对齐（保持默认）
        self._set_spacing(pPr)
        self._set_indent(pPr, left='0')
        self._set_run_font(para, FONT_SIZE_BODY, bold=False)

    def _set_alignment(self, pPr: Any, align: str) -> None:
        """设置对齐方式"""
        # 移除旧的对齐
        old_jc = pPr.find(qn('w:jc'))
        if old_jc is not None:
            pPr.remove(old_jc)

        jc = OxmlElement('w:jc')
        jc.set(qn('w:val'), align)
        pPr.append(jc)

    def _set_spacing(self, pPr: Any, before: str = '0', after: str = '0') -> None:
        """设置行距和段间距"""
        spacing = OxmlElement('w:spacing')
        spacing.set(qn('w:line'), str(LINE_SPACING))
        spacing.set(qn('w:lineRule'), 'auto')
        spacing.set(qn('w:before'), before)
        spacing.set(qn('w:after'), after)
        pPr.append(spacing)

    def _set_indent(self, pPr: Any, first_line: str = '0', left: str = '0') -> None:
        """设置缩进"""
        ind = OxmlElement('w:ind')
        if first_line != '0':
            ind.set(qn('w:firstLine'), first_line)
        # 总是设置 left（包括 0）
        ind.set(qn('w:left'), left)
        pPr.append(ind)

    def _set_numbering(self, pPr: Any, num_id: str, ilvl: str) -> None:
        """设置编号"""
        # 移除旧的编号
        old_numPr = pPr.find(qn('w:numPr'))
        if old_numPr is not None:
            pPr.remove(old_numPr)

        numPr = OxmlElement('w:numPr')
        ilvl_el = OxmlElement('w:ilvl')
        ilvl_el.set(qn('w:val'), ilvl)
        numPr.append(ilvl_el)

        numId = OxmlElement('w:numId')
        numId.set(qn('w:val'), num_id)
        numPr.append(numId)

        pPr.append(numPr)

    def _set_run_font(self, para: Any, size: int, bold: bool = False) -> None:
        """设置 run 的字体和字号"""
        for run in para.runs:
            rPr = run._element.get_or_add_rPr()

            # 清除旧字体设置
            old_rFonts = rPr.find(qn('w:rFonts'))
            if old_rFonts is not None:
                rPr.remove(old_rFonts)

            # 设置新字体
            rFonts = OxmlElement('w:rFonts')
            rFonts.set(qn('w:ascii'), FONT_ENGLISH)
            rFonts.set(qn('w:hAnsi'), FONT_ENGLISH)
            rFonts.set(qn('w:eastAsia'), FONT_CHINESE)
            rFonts.set(qn('w:cs'), FONT_ENGLISH)
            rPr.insert(0, rFonts)

            # 清除旧字号
            for tag in ['w:sz', 'w:szCs']:
                old = rPr.find(qn(tag))
                if old is not None:
                    rPr.remove(old)

            # 设置字号
            sz = OxmlElement('w:sz')
            sz.set(qn('w:val'), str(size))
            rPr.append(sz)

            szCs = OxmlElement('w:szCs')
            szCs.set(qn('w:val'), str(size))
            rPr.append(szCs)

            # 清除旧加粗
            old_b = rPr.find(qn('w:b'))
            if old_b is not None:
                rPr.remove(old_b)

            # 设置加粗
            if bold:
                b = OxmlElement('w:b')
                rPr.append(b)
