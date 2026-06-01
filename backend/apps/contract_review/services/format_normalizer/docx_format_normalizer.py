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

        # 创建 abstractNum（抽象编号定义）
        abstractNum = OxmlElement('w:abstractNum')
        abstractNum.set(qn('w:abstractNumId'), '100')

        # 一级：一、二、三...
        lvl0 = self._create_level(
            ilvl='0',
            num_fmt='chineseCounting',
            level_text='%1、',
            left='420',
            hanging='420'
        )
        abstractNum.append(lvl0)

        # 二级：（一）（二）...
        lvl1 = self._create_level(
            ilvl='1',
            num_fmt='chineseCounting',
            level_text='（%2）',
            left='840',
            hanging='420'
        )
        abstractNum.append(lvl1)

        # 三级：1. 2. 3.
        lvl2 = self._create_level(
            ilvl='2',
            num_fmt='decimal',
            level_text='%3.',
            left='1260',
            hanging='420'
        )
        abstractNum.append(lvl2)

        # 四级：（1）（2）...
        lvl3 = self._create_level(
            ilvl='3',
            num_fmt='decimal',
            level_text='（%4）',
            left='1680',
            hanging='420'
        )
        abstractNum.append(lvl3)

        # 插入到 numbering 元素开头
        numbering_elm.insert(0, abstractNum)

        # 创建 num 实例
        num = OxmlElement('w:num')
        num.set(qn('w:numId'), '100')
        abstractNumRef = OxmlElement('w:abstractNumId')
        abstractNumRef.set(qn('w:val'), '100')
        num.append(abstractNumRef)
        numbering_elm.append(num)

        # 如果是新创建的 part，需要更新其内容
        if hasattr(self, '_numbering_part'):
            from lxml import etree
            self._numbering_part._blob = etree.tostring(numbering_elm, xml_declaration=True, encoding='UTF-8', standalone=True)

        logger.debug("编号样式已创建")

    def _create_level(self, ilvl: str, num_fmt: str, level_text: str, left: str, hanging: str) -> OxmlElement:
        """创建编号级别定义"""
        lvl = OxmlElement('w:lvl')
        lvl.set(qn('w:ilvl'), ilvl)

        start = OxmlElement('w:start')
        start.set(qn('w:val'), '1')
        lvl.append(start)

        numFmt = OxmlElement('w:numFmt')
        numFmt.set(qn('w:val'), num_fmt)
        lvl.append(numFmt)

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

        logger.debug("段落格式已规范化")

    def _classify_paragraph(self, para: Any) -> str:
        """分类段落类型"""
        text = para.text.strip()

        # 空行
        if not text:
            return 'empty'

        # 标题（合同标题）
        if self._is_contract_title(text):
            return 'title'

        # 条标题（第一条、第二条...）
        if self._is_article_title(text):
            return 'article_title'

        # 款标题（（一）、（二）...）
        if self._is_clause_title(text):
            return 'clause_title'

        # 项标题（1. 2. 3....）
        if self._is_item_title(text):
            return 'item_title'

        # 当事人信息（甲方、乙方...）
        if self._is_party_info(text):
            return 'party_info'

        # 默认为正文
        return 'body'

    def _is_contract_title(self, text: str) -> bool:
        """判断是否为合同标题"""
        title_keywords = ['合同', '协议', '契约', '合约']
        return any(kw in text for kw in title_keywords) and len(text) < 30

    def _is_article_title(self, text: str) -> bool:
        """判断是否为条标题（第X条）"""
        return bool(re.match(r'^第[一二三四五六七八九十百]+条', text))

    def _is_clause_title(self, text: str) -> bool:
        """判断是否为款标题（（X））"""
        return bool(re.match(r'^（[一二三四五六七八九十]+）', text))

    def _is_item_title(self, text: str) -> bool:
        """判断是否为项标题（X.）"""
        return bool(re.match(r'^\d+[.、]', text))

    def _is_party_info(self, text: str) -> bool:
        """判断是否为当事人信息"""
        party_patterns = [
            r'^甲方[：:]',
            r'^乙方[：:]',
            r'^丙方[：:]',
            r'^丁方[：:]',
            r'^法定代表人[：:]',
            r'^地址[：:]',
            r'^联系人[：:]',
            r'^电话[：:]',
            r'^统一社会信用代码[：:]',
        ]
        return any(re.match(p, text) for p in party_patterns)

    def _apply_paragraph_format(self, para: Any, para_type: str) -> None:
        """应用段落格式"""
        pPr = para._element.get_or_add_pPr()

        # 清除旧的格式（保留必要的）
        self._clear_old_format(pPr)

        # 根据类型设置格式
        if para_type == 'empty':
            self._apply_empty_format(pPr)
        elif para_type == 'title':
            self._apply_title_format(para, pPr)
        elif para_type == 'article_title':
            self._apply_article_title_format(para, pPr)
        elif para_type == 'clause_title':
            self._apply_clause_title_format(para, pPr)
        elif para_type == 'item_title':
            self._apply_item_title_format(para, pPr)
        elif para_type == 'party_info':
            self._apply_party_info_format(para, pPr)
        else:  # body
            self._apply_body_format(para, pPr)

    def _clear_old_format(self, pPr: Any) -> None:
        """清除旧的格式定义"""
        # 保留 numPr（编号）和 jc（对齐），清除 spacing 和 ind
        for tag in ['w:spacing', 'w:ind']:
            old = pPr.find(qn(tag))
            if old is not None:
                pPr.remove(old)

    def _apply_empty_format(self, pPr: Any) -> None:
        """空行格式"""
        spacing = OxmlElement('w:spacing')
        spacing.set(qn('w:line'), str(LINE_SPACING))
        spacing.set(qn('w:lineRule'), 'auto')
        spacing.set(qn('w:before'), '0')
        spacing.set(qn('w:after'), '0')
        pPr.append(spacing)

    def _apply_title_format(self, para: Any, pPr: Any) -> None:
        """合同标题格式：居中、加粗、大字号"""
        # 对齐
        self._set_alignment(pPr, 'center')

        # 行距
        self._set_spacing(pPr, before='0', after='0')

        # 字体
        self._set_run_font(para, FONT_SIZE_TITLE, bold=True)

    def _apply_article_title_format(self, para: Any, pPr: Any) -> None:
        """条标题格式：左对齐、加粗、编号"""
        # 对齐
        self._set_alignment(pPr, 'left')

        # 行距
        self._set_spacing(pPr, before='0', after='0')

        # 设置编号
        self._set_numbering(pPr, num_id='100', ilvl='0')

        # 字体
        self._set_run_font(para, FONT_SIZE_BODY, bold=True)

    def _apply_clause_title_format(self, para: Any, pPr: Any) -> None:
        """款标题格式：左对齐、编号"""
        # 对齐
        self._set_alignment(pPr, 'left')

        # 行距
        self._set_spacing(pPr, before='0', after='0')

        # 设置编号
        self._set_numbering(pPr, num_id='100', ilvl='1')

        # 字体
        self._set_run_font(para, FONT_SIZE_BODY, bold=False)

    def _apply_item_title_format(self, para: Any, pPr: Any) -> None:
        """项标题格式：左对齐、编号"""
        # 对齐
        self._set_alignment(pPr, 'left')

        # 行距
        self._set_spacing(pPr, before='0', after='0')

        # 设置编号
        self._set_numbering(pPr, num_id='100', ilvl='2')

        # 字体
        self._set_run_font(para, FONT_SIZE_BODY, bold=False)

    def _apply_party_info_format(self, para: Any, pPr: Any) -> None:
        """当事人信息格式：左对齐"""
        # 对齐
        self._set_alignment(pPr, 'left')

        # 行距
        self._set_spacing(pPr, before='0', after='0')

        # 字体
        self._set_run_font(para, FONT_SIZE_BODY, bold=False)

    def _apply_body_format(self, para: Any, pPr: Any) -> None:
        """正文格式：两端对齐、首行缩进"""
        # 对齐
        self._set_alignment(pPr, 'both')

        # 行距
        self._set_spacing(pPr, before='0', after='0')

        # 首行缩进
        self._set_indent(pPr, first_line=str(FIRST_LINE_INDENT))

        # 字体
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
        if left != '0':
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
