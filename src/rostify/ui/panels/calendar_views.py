"""Month and Year calendar views — the Schedule page's "Year -> Month ->
Custom -> Day" drill-down (see CLAUDE.md, "Reference material": this scale
switcher and the day-cell "template chip" look come from
reference/RostaStudioSchedule.jsx's Month/Year views, ported as design only).

A day cell's chip is a `Template` assigned to (subdepartment, date) via
`core.templates.TemplateAssignment` — the same record the Custom view reads
and writes. This is deliberately just a second, calendar-shaped way to see
and set the same day-plan data, not a new entity.

Both grids are *painted*, not built from widgets: the Month grid is one
widget drawing 42 day cells, and each Year mini-month is one widget drawing
its 42 days. The earlier version made a styled QPushButton per day (500+ on
the Year page, each with its own stylesheet), which was slow to build and
left rounded button backgrounds overlapping each other. Painting also gives
the Month view's day cards their "glass" look: translucent, with a sheen.

Interaction: click a day number to jump to Day view; click a template chip
(or the pencil that appears on hover) to change a day's template; the trash
icon clears it; hovering an empty day shows a "+" to add one. Drag a
template from the list beside the month onto a day, or drag a day's chip to
another day to move it (hold Ctrl to copy). In the Year view, click a month
name to open that month, a day to open Day view.

Every change to a day's template re-times the shifts already assigned on
that day (services/shift_sync.py).
"""

from __future__ import annotations

import calendar
from collections.abc import Callable
from datetime import date, timedelta

from PySide6.QtCore import QByteArray, QEvent, QMimeData, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QDrag, QFont, QFontMetrics, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QHBoxLayout,
    QAbstractItemView,
    QApplication,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from rostify.core.schedule import Schedule
from rostify.core.templates import Template, TemplateAssignment, natural_key
from rostify.services.persistence import Repository
from rostify.services.shift_sync import retime_day, shift_assignments

from .. import icons
from ..theme import COLORS, TEMPLATE_COLOR_HEX, is_dark, template_ink
from .widgets import color_dot_icon, icon_button

_WEEKDAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]  # weekStartsOn = Sunday, per the reference
_NO_TEMPLATE = "— none —"
_WEEKS = 6
#: Drag payload: "<template id>" from the palette, or
#: "<template id>|<source ISO date>" when a day's chip is dragged.
TEMPLATE_MIME = "application/x-rostify-template"


def _template_drag_data(template_id: str, source: date | None = None) -> QMimeData:
    data = QMimeData()
    payload = template_id if source is None else f"{template_id}|{source.isoformat()}"
    data.setData(TEMPLATE_MIME, QByteArray(payload.encode("utf-8")))
    return data


def _read_template_drag(mime: QMimeData) -> tuple[str, date | None] | None:
    if not mime.hasFormat(TEMPLATE_MIME):
        return None
    template_id, _, source = bytes(mime.data(TEMPLATE_MIME)).decode("utf-8").partition("|")
    return template_id, (date.fromisoformat(source) if source else None)


def _sunday_on_or_before(day: date) -> date:
    # Python's Monday=0..Sunday=6; days back to the most recent Sunday.
    return day - timedelta(days=(day.weekday() + 1) % 7)


def _add_months(day: date, delta: int) -> date:
    month_index = day.month - 1 + delta
    year = day.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, 1)


def _color(value: str, alpha: float | None = None) -> QColor:
    """A token (hex or `rgba(...)` string) as a QColor, optionally with its
    alpha replaced."""
    if value.startswith("rgba("):
        r, g, b, a = (part.strip() for part in value[5:-1].split(","))
        color = QColor(int(r), int(g), int(b))
        color.setAlphaF(float(a))
    else:
        color = QColor(value)
    if alpha is not None:
        color.setAlphaF(alpha)
    return color


def _font(base: QFont, pixel_size: int, weight: QFont.Weight = QFont.Normal) -> QFont:
    font = QFont(base)
    font.setPixelSize(pixel_size)
    font.setWeight(weight)
    return font


def _template_hex(template: Template) -> str:
    return TEMPLATE_COLOR_HEX.get(template.color, TEMPLATE_COLOR_HEX["blue"])


_icon_cache: dict[tuple[str, str], object] = {}


def _icon_pixmap(name: str, color: str, size: int = 14):
    key = (name, color)
    if key not in _icon_cache:
        _icon_cache[key] = icons.icon(name, color, size).pixmap(size, size)
    return _icon_cache[key]


class _AssignTemplateDialog(QDialog):
    def __init__(self, templates: list[Template], current: Template | None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Assign template")
        self.combo = QComboBox()
        self.combo.addItem(_NO_TEMPLATE)
        self.combo.addItems([t.name for t in templates])
        if current is not None:
            index = self.combo.findText(current.name)
            if index >= 0:
                self.combo.setCurrentIndex(index)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Template for this day"))
        layout.addWidget(self.combo)
        layout.addWidget(buttons)

    def chosen_name(self) -> str:
        return self.combo.currentText()


# --- Month ------------------------------------------------------------------


class _MonthCanvas(QWidget):
    """The whole 6-week month grid, painted: a soft backdrop, weekday
    heads, week numbers and 42 glass day cards.

    Each card is split 1/3 date (top) and 2/3 template chip (bottom).
    Days of the neighbouring months keep the same card; only their number
    and chip are dimmed, so they stay readable in light mode.
    """

    day_clicked = Signal(date)
    chip_clicked = Signal(date)
    remove_requested = Signal(date)
    #: (target day, template id, source day or None, copy?)
    template_dropped = Signal(date, str, object, bool)

    _MARGIN = 12
    _HEAD_HEIGHT = 22
    _WEEK_COL_WIDTH = 30
    _SPACING = 6
    _RADIUS = 10

    def __init__(self, accent_hex: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._accent_hex = accent_hex
        self._anchor = date.today().replace(day=1)
        self._templates: dict[date, Template] = {}
        self._hover: tuple[int, str] | None = None  # (cell index, part)
        self._press: tuple[QPointF, tuple[int, str] | None] | None = None
        self._dragged = False  # a drag started from the last press: no click
        self._drop_index: int | None = None  # day highlighted under a drag
        self._headcount: dict[date, int] = {}
        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        # Small enough to fit a 1366x768 laptop screen: a larger minimum
        # makes the whole window grow when this page opens, which shifts
        # the sidebar under the user's mouse.
        self.setMinimumSize(7 * 80 + self._WEEK_COL_WIDTH, _WEEKS * 52 + self._HEAD_HEIGHT)

    def set_month(self, anchor: date, templates: dict[date, Template], headcount: dict[date, int] | None = None) -> None:
        """`headcount`: how many employees have a shift on each day."""
        self._anchor = anchor
        self._templates = templates
        self._headcount = headcount or {}
        self.update()

    # --- geometry ---------------------------------------------------------

    def _start(self) -> date:
        return _sunday_on_or_before(self._anchor)

    def _day(self, index: int) -> date:
        return self._start() + timedelta(days=index)

    def _cell_rect(self, index: int) -> QRectF:
        m, sp = self._MARGIN, self._SPACING
        width = self.width() - 2 * m - self._WEEK_COL_WIDTH
        height = self.height() - 2 * m - self._HEAD_HEIGHT
        cell_w = (width - 6 * sp) / 7
        cell_h = (height - (_WEEKS - 1) * sp) / _WEEKS
        row, col = divmod(index, 7)
        x = m + self._WEEK_COL_WIDTH + col * (cell_w + sp)
        y = m + self._HEAD_HEIGHT + row * (cell_h + sp)
        return QRectF(x, y, cell_w, cell_h)

    def _parts(self, index: int) -> dict[str, QRectF]:
        """Clickable areas of one card: the day number, the chip (bottom
        2/3), and the two hover icons in the date row."""
        cell = self._cell_rect(index)
        date_h = cell.height() / 3
        circle = min(26.0, date_h - 4)
        number = QRectF(cell.left() + 6, cell.top() + (date_h - circle) / 2 + 1, circle, circle)
        chip = QRectF(cell.left() + 5, cell.top() + date_h, cell.width() - 10, cell.height() - date_h - 5)
        icon = 20.0
        remove = QRectF(cell.right() - 6 - icon, cell.top() + (date_h - icon) / 2 + 1, icon, icon)
        edit = remove.translated(-(icon + 4), 0)
        return {"number": number, "chip": chip, "edit": edit, "remove": remove}

    def _hit(self, pos: QPointF) -> tuple[int, str] | None:
        for index in range(_WEEKS * 7):
            if not self._cell_rect(index).contains(pos):
                continue
            has_template = self._day(index) in self._templates
            parts = self._parts(index)
            if has_template:
                for name in ("edit", "remove"):
                    if parts[name].contains(pos):
                        return index, name
            for name in ("number", "chip"):
                if parts[name].contains(pos):
                    return index, name
            return index, "card"
        return None

    # --- painting ---------------------------------------------------------

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)
        self._paint_backdrop(painter)
        self._paint_heads(painter)
        today = date.today()
        next_month = _add_months(self._anchor, 1)
        for index in range(_WEEKS * 7):
            day = self._day(index)
            self._paint_cell(painter, index, day, self._anchor <= day < next_month, day == today)
        painter.end()

    def _paint_backdrop(self, painter: QPainter) -> None:
        """A plain frame around the grid — the glass look belongs to the day
        cards only."""
        area = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        painter.setPen(QPen(_color(COLORS["border_default"]), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(area, 14, 14)

    def _paint_heads(self, painter: QPainter) -> None:
        painter.setFont(_font(self.font(), 10, QFont.Bold))
        painter.setPen(_color(COLORS["text_tertiary"]))
        m = self._MARGIN
        painter.drawText(QRectF(m, m, self._WEEK_COL_WIDTH, self._HEAD_HEIGHT), Qt.AlignCenter, "WK")
        for col, label in enumerate(_WEEKDAY_LABELS):
            cell = self._cell_rect(col)
            head = QRectF(cell.left(), m, cell.width(), self._HEAD_HEIGHT)
            painter.drawText(head, Qt.AlignCenter, label.upper())
        painter.setFont(_font(self.font(), 11, QFont.Bold))
        for week in range(_WEEKS):
            cell = self._cell_rect(week * 7)
            week_start = self._day(week * 7)
            gutter = QRectF(m, cell.top(), self._WEEK_COL_WIDTH, cell.height())
            painter.drawText(gutter, Qt.AlignCenter, str(week_start.isocalendar()[1]))

    def _paint_cell(self, painter: QPainter, index: int, day: date, in_month: bool, is_today: bool) -> None:
        cell = self._cell_rect(index)
        parts = self._parts(index)
        hovered = self._hover is not None and self._hover[0] == index
        dark = is_dark()

        # Glass card: a translucent fill, a sheen fading down from the top
        # edge, and a light hairline.
        path = QPainterPath()
        path.addRoundedRect(cell, self._RADIUS, self._RADIUS)
        painter.setPen(Qt.NoPen)
        painter.setBrush(_color("#ffffff", (0.07 if hovered else 0.045) if dark else (0.78 if hovered else 0.6)))
        painter.drawPath(path)
        sheen = QLinearGradient(cell.topLeft(), QPointF(cell.left(), cell.top() + cell.height() * 0.6))
        sheen.setColorAt(0.0, _color("#ffffff", 0.07 if dark else 0.5))
        sheen.setColorAt(1.0, _color("#ffffff", 0.0))
        painter.setBrush(sheen)
        painter.drawPath(path)
        if index == self._drop_index:
            border = QPen(_color(self._accent_hex), 2.5)
        elif is_today:
            border = QPen(_color(self._accent_hex, 0.75), 1.5)
        elif dark:
            border = QPen(_color("#ffffff", 0.16 if hovered else 0.10), 1)
        else:
            border = QPen(_color("#000000", 0.14 if hovered else 0.08), 1)
        painter.setPen(border)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)

        # Day number (1/3 of the card).
        number = parts["number"]
        painter.setFont(_font(self.font(), 12, QFont.Bold if is_today else QFont.DemiBold))
        if is_today:
            painter.setPen(Qt.NoPen)
            painter.setBrush(_color(self._accent_hex))
            painter.drawEllipse(number)
            painter.setPen(_color(COLORS["accent_on"]))
        else:
            if hovered and self._hover[1] == "number":
                painter.setPen(Qt.NoPen)
                painter.setBrush(_color(COLORS["bg_hover"]))
                painter.drawEllipse(number)
            painter.setPen(_color(COLORS["text_primary"] if in_month else COLORS["text_tertiary"]))
        painter.drawText(number, Qt.AlignCenter, str(day.day))

        # Headcount in the date row, right side — makes way for the hover
        # icons when the day has a template.
        count = self._headcount.get(day, 0)
        if count and not (hovered and day in self._templates):
            painter.save()
            if not in_month:
                painter.setOpacity(0.5)
            count_rect = QRectF(parts["edit"].left() - 8, parts["edit"].top(), parts["remove"].right() - parts["edit"].left() + 8, parts["edit"].height())
            painter.setFont(_font(self.font(), 11, QFont.DemiBold))
            painter.setPen(_color(COLORS["text_secondary"]))
            text_width = QFontMetrics(painter.font()).horizontalAdvance(str(count))
            painter.drawText(count_rect, Qt.AlignRight | Qt.AlignVCenter, str(count))
            icon = _icon_pixmap("staff", COLORS["text_tertiary"], 13)
            painter.drawPixmap(
                QPointF(count_rect.right() - text_width - 16, count_rect.center().y() - 6.5), icon
            )
            painter.restore()

        # Template chip (the other 2/3).
        template = self._templates.get(day)
        chip = parts["chip"]
        if template is not None:
            painter.save()
            if not in_month:
                painter.setOpacity(0.5)
            self._paint_chip(painter, chip, template, hovered and self._hover[1] in ("chip", "edit"))
            painter.restore()
            if hovered:
                for name, icon_name, color in (
                    ("edit", "pencil", COLORS["text_primary"]),
                    ("remove", "trash", COLORS["danger"]),
                ):
                    rect = parts[name]
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(_color(COLORS["bg_hover"] if self._hover[1] == name else COLORS["bg_control"]))
                    painter.drawRoundedRect(rect, 5, 5)
                    pixmap = _icon_pixmap(icon_name, color)
                    painter.drawPixmap(
                        QPointF(rect.center().x() - 7, rect.center().y() - 7), pixmap
                    )
        elif hovered:
            dash = QPen(_color(COLORS["border_strong"]), 1, Qt.DashLine)
            painter.setPen(dash)
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(chip.adjusted(0.5, 0.5, -0.5, -0.5), 8, 8)
            painter.setPen(_color(COLORS["text_secondary"]))
            painter.setFont(_font(self.font(), 16))
            painter.drawText(chip, Qt.AlignCenter, "+")

    def _paint_chip(self, painter: QPainter, chip: QRectF, template: Template, hovered: bool) -> None:
        hex_color = _template_hex(template)
        painter.setPen(Qt.NoPen)
        painter.setBrush(_color(hex_color, (0.30 if hovered else 0.22) if is_dark() else (0.34 if hovered else 0.26)))
        painter.drawRoundedRect(chip, 8, 8)
        # A solid stripe down the left edge carries the color even where
        # the tint is faint.
        stripe = QRectF(chip.left(), chip.top() + 6, 3, max(chip.height() - 12, 4))
        painter.setBrush(_color(hex_color))
        painter.drawRoundedRect(stripe, 1.5, 1.5)

        text_rect = chip.adjusted(10, 4, -6, -4)
        name_font = _font(self.font(), 12, QFont.DemiBold)
        name_metrics = QFontMetrics(name_font)
        name = name_metrics.elidedText(template.name, Qt.ElideRight, int(text_rect.width()))
        show_subtitle = bool(template.subtitle) and text_rect.height() >= name_metrics.height() * 2 + 2
        painter.setFont(name_font)
        painter.setPen(_color(template_ink(hex_color)))
        if not show_subtitle:
            painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, name)
            return
        sub_font = _font(self.font(), 11)
        sub_metrics = QFontMetrics(sub_font)
        block = name_metrics.height() + sub_metrics.height()
        top = text_rect.top() + (text_rect.height() - block) / 2
        painter.drawText(QRectF(text_rect.left(), top, text_rect.width(), name_metrics.height()), Qt.AlignLeft, name)
        painter.setFont(sub_font)
        painter.setPen(_color(COLORS["text_secondary"]))
        subtitle = sub_metrics.elidedText(template.subtitle, Qt.ElideRight, int(text_rect.width()))
        painter.drawText(
            QRectF(text_rect.left(), top + name_metrics.height(), text_rect.width(), sub_metrics.height()),
            Qt.AlignLeft,
            subtitle,
        )

    # --- mouse --------------------------------------------------------------

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self._press = (event.position(), self._hit(event.position()))
            self._dragged = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._press is not None and event.buttons() & Qt.LeftButton and not self._dragged:
            origin, hit = self._press
            moved = (event.position() - origin).manhattanLength() >= QApplication.startDragDistance()
            if moved and hit is not None and hit[1] in ("chip", "edit"):
                day = self._day(hit[0])
                template = self._templates.get(day)
                if template is not None:
                    self._dragged = True
                    self._start_chip_drag(hit[0], day, template)
                    return
        hit = self._hit(event.position())
        if hit != self._hover:
            self._hover = hit
            clickable = hit is not None and hit[1] in ("number", "chip", "edit", "remove")
            self.setCursor(Qt.PointingHandCursor if clickable else Qt.ArrowCursor)
            self.update()
        super().mouseMoveEvent(event)

    def _start_chip_drag(self, index: int, day: date, template: Template) -> None:
        drag = QDrag(self)
        drag.setMimeData(_template_drag_data(template.id, day))
        chip = self._parts(index)["chip"].toRect()
        drag.setPixmap(self.grab(chip))
        drag.setHotSpot(chip.center() - chip.topLeft())
        drag.exec(Qt.MoveAction | Qt.CopyAction, Qt.MoveAction)
        self._press = None

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = None
        self.setCursor(Qt.ArrowCursor)
        self.update()
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        pressed, self._press = self._press, None
        if event.button() != Qt.LeftButton or self._dragged or pressed is None:
            return
        hit = self._hit(event.position())
        if hit is None:
            return
        index, part = hit
        day = self._day(index)
        if part == "number":
            self.day_clicked.emit(day)
        elif part in ("chip", "edit"):
            self.chip_clicked.emit(day)
        elif part == "remove":
            self.remove_requested.emit(day)

    # --- drop target -------------------------------------------------------

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasFormat(TEMPLATE_MIME):
            event.acceptProposedAction()

    def dragMoveEvent(self, event) -> None:  # noqa: N802
        hit = self._hit(event.position())
        index = hit[0] if hit is not None else None
        if index != self._drop_index:
            self._drop_index = index
            self.update()
        if index is None:
            event.ignore()
            return
        copy = bool(event.modifiers() & Qt.ControlModifier)
        event.setDropAction(Qt.CopyAction if copy else Qt.MoveAction)
        event.accept()

    def dragLeaveEvent(self, event) -> None:  # noqa: N802
        self._drop_index = None
        self.update()

    def dropEvent(self, event) -> None:  # noqa: N802
        self._drop_index = None
        self.update()
        payload = _read_template_drag(event.mimeData())
        hit = self._hit(event.position())
        if payload is None or hit is None:
            event.ignore()
            return
        template_id, source = payload
        copy = bool(event.modifiers() & Qt.ControlModifier)
        event.setDropAction(Qt.CopyAction if copy else Qt.MoveAction)
        event.accept()
        self.template_dropped.emit(self._day(hit[0]), template_id, source, copy)

    def event(self, event) -> bool:
        if event.type() == QEvent.ToolTip:
            hit = self._hit(QPointF(event.pos()))
            template = self._templates.get(self._day(hit[0])) if hit else None
            if template is not None and hit[1] in ("chip", "edit", "remove"):
                text = template.name if not template.subtitle else f"{template.name}\n{template.subtitle}"
                tips = {"edit": "Change this day's template", "remove": "Remove template from this day"}
                QToolTip.showText(event.globalPos(), tips.get(hit[1], text), self)
            elif hit is not None and hit[1] == "chip":
                QToolTip.showText(event.globalPos(), "Add a template to this day", self)
            elif hit is not None and hit[1] == "number":
                QToolTip.showText(event.globalPos(), "Open this day", self)
            elif hit is not None and self._headcount.get(self._day(hit[0])):
                QToolTip.showText(event.globalPos(), f"{self._headcount[self._day(hit[0])]} employees on shift", self)
            else:
                QToolTip.hideText()
            return True
        return super().event(event)


class _PaletteItemDelegate(QStyledItemDelegate):
    """Template name, and its comment underneath in small grey text."""

    def paint(self, painter, option, index) -> None:
        subtitle = index.data(Qt.UserRole + 1) or ""
        if not subtitle:
            super().paint(painter, option, index)
            return
        painter.save()
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        opt.text = ""
        QApplication.style().drawControl(QStyle.CE_ItemViewItem, opt, painter, opt.widget)
        text_left = option.rect.left() + 28
        top_half = QRectF(text_left, option.rect.top() + 3, option.rect.width() - 32, option.rect.height() / 2 - 1)
        bottom_half = top_half.translated(0, option.rect.height() / 2 - 2)
        painter.setPen(_color(COLORS["text_primary"]))
        painter.drawText(top_half, Qt.AlignLeft | Qt.AlignVCenter, index.data(Qt.DisplayRole))
        small = _font(option.font, 11)
        painter.setFont(small)
        painter.setPen(_color(COLORS["text_tertiary"]))
        elided = QFontMetrics(small).elidedText(subtitle, Qt.ElideRight, int(bottom_half.width()))
        painter.drawText(bottom_half, Qt.AlignLeft | Qt.AlignVCenter, elided)
        painter.restore()

    def sizeHint(self, option, index):  # noqa: N802
        size = super().sizeHint(option, index)
        if index.data(Qt.UserRole + 1):
            size.setHeight(max(size.height(), 40))
        return size


class _TemplatePalette(QListWidget):
    """The subdepartment's templates, to drag onto days of the month."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setItemDelegate(_PaletteItemDelegate(self))
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragOnly)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setFixedWidth(200)
        self.setToolTip("Drag a template onto a day")

    def set_templates(self, templates: list[Template]) -> None:
        self.clear()
        for template in sorted(templates, key=lambda t: natural_key(t.name)):
            item = QListWidgetItem(color_dot_icon(_template_hex(template)), template.name)
            item.setData(Qt.UserRole, template.id)
            item.setData(Qt.UserRole + 1, template.subtitle)  # shown under the name
            item.setToolTip(f"{template.name}\n{template.subtitle}" if template.subtitle else template.name)
            self.addItem(item)

    def startDrag(self, supported_actions) -> None:  # noqa: N802
        item = self.currentItem()
        if item is None:
            return
        drag = QDrag(self)
        drag.setMimeData(_template_drag_data(item.data(Qt.UserRole)))
        drag.setPixmap(self.viewport().grab(self.visualItemRect(item)))
        drag.exec(Qt.CopyAction, Qt.CopyAction)


class MonthGridView(QWidget):
    day_requested = Signal(date)
    #: "Open in Templates" on the Templates panel, with the subdepartment.
    templates_requested = Signal(str)

    def __init__(
        self,
        repository: Repository,
        on_change: Callable[[], None] | None = None,
        accent_hex: str | None = None,
        parent: QWidget | None = None,
        schedule: Schedule | None = None,
        panel_open: bool = True,
        on_panel_toggled: Callable[[bool], None] | None = None,
    ) -> None:
        """The subdepartment comes from the Schedule page's shared selector
        (`set_subdepartment`); the month navigation lives in
        `period_controls`, which that page shows in its top row."""
        super().__init__(parent)
        self._repository = repository
        self._schedule = schedule
        self._on_change = on_change
        self._on_panel_toggled = on_panel_toggled
        self._subdepartment = ""
        self._anchor = date.today().replace(day=1)
        self._templates: list[Template] = []
        self._assignments: dict[date, str] = {}  # date -> template_id

        prev_button = QPushButton("<")
        prev_button.setFixedWidth(32)
        prev_button.setToolTip("Previous month")
        prev_button.clicked.connect(lambda: self._step(-1))
        next_button = QPushButton(">")
        next_button.setFixedWidth(32)
        next_button.setToolTip("Next month")
        next_button.clicked.connect(lambda: self._step(1))
        today_button = QPushButton("Today")
        today_button.setToolTip("Jump to the current month")
        today_button.clicked.connect(self._go_today)
        self.period_label = QLabel()
        self.period_label.setStyleSheet("font-weight: 600; font-size: 14px;")

        self.period_controls = QWidget()
        nav_row = QHBoxLayout(self.period_controls)
        nav_row.setContentsMargins(0, 0, 0, 0)
        nav_row.addWidget(prev_button)
        nav_row.addWidget(self.period_label)
        nav_row.addWidget(next_button)
        nav_row.addWidget(today_button)

        self.canvas = _MonthCanvas(accent_hex or COLORS["accent"])
        self.canvas.day_clicked.connect(self.day_requested.emit)
        self.canvas.chip_clicked.connect(self._on_chip_clicked)
        self.canvas.remove_requested.connect(self._on_remove_clicked)
        self.canvas.template_dropped.connect(self._on_template_dropped)

        # The Templates panel on the right: collapses to a thin strip with
        # the same ☰ button the sidebar uses, and links to the Templates tab.
        self.palette = _TemplatePalette()
        palette_title = QLabel("Templates")
        palette_title.setProperty("role", "heading")
        open_button = icon_button("↗", "Open these templates in the Templates tab")
        open_button.clicked.connect(lambda: self.templates_requested.emit(self._subdepartment))
        hide_button = icon_button("☰", "Hide the Templates panel")
        hide_button.clicked.connect(lambda: self._set_panel_open(False))
        title_row = QHBoxLayout()
        title_row.addWidget(palette_title)
        title_row.addStretch(1)
        title_row.addWidget(open_button)
        title_row.addWidget(hide_button)
        palette_hint = QLabel("Drag onto a day.\nDrag a day's template to move it,\nhold Ctrl to copy.")
        palette_hint.setProperty("role", "hint")
        self._panel = QWidget()
        side = QVBoxLayout(self._panel)
        side.setContentsMargins(0, 0, 0, 0)
        side.setSpacing(6)
        side.addLayout(title_row)
        side.addWidget(palette_hint)
        side.addWidget(self.palette, stretch=1)

        self._show_panel_button = icon_button("☰", "Show the Templates panel (drag templates onto days)")
        self._show_panel_button.clicked.connect(lambda: self._set_panel_open(True))

        body = QHBoxLayout(self)
        body.addWidget(self.canvas, stretch=1)
        body.addWidget(self._panel)
        body.addWidget(self._show_panel_button, 0, Qt.AlignTop)
        self._set_panel_open(panel_open, notify=False)

    def _set_panel_open(self, visible: bool, notify: bool = True) -> None:
        self._panel.setVisible(visible)
        self._show_panel_button.setVisible(not visible)
        if notify and self._on_panel_toggled:
            self._on_panel_toggled(visible)

    def set_subdepartment(self, subdepartment: str) -> None:
        self._subdepartment = subdepartment
        self._render()

    def showEvent(self, event) -> None:  # noqa: N802
        """Data is read when the page is shown, not when it is built."""
        super().showEvent(event)
        self._render()

    def set_anchor(self, day: date) -> None:
        self._anchor = day.replace(day=1)
        self._render()

    def _step(self, delta_months: int) -> None:
        self._anchor = _add_months(self._anchor, delta_months)
        self._render()

    def _go_today(self) -> None:
        self._anchor = date.today().replace(day=1)
        self._render()

    def _render(self) -> None:
        self.period_label.setText(self._anchor.strftime("%B %Y"))
        if not self.isVisible():
            return  # showEvent renders when the page is actually opened

        subdepartment = self._subdepartment
        self._templates = self._repository.load_templates(subdepartment) if subdepartment else []
        templates_by_id = {t.id: t for t in self._templates}
        self.palette.set_templates(self._templates)

        start = _sunday_on_or_before(self._anchor)
        self._assignments = {}
        if subdepartment:
            range_end = start + timedelta(days=_WEEKS * 7 - 1)
            for ta in self._repository.load_template_assignments_range(subdepartment, start, range_end):
                self._assignments[ta.date] = ta.template_id

        by_day = {
            day: templates_by_id[template_id]
            for day, template_id in self._assignments.items()
            if template_id in templates_by_id
        }
        headcount = {}
        if self._schedule is not None and subdepartment:
            for offset in range(_WEEKS * 7):
                day = start + timedelta(days=offset)
                headcount[day] = len(shift_assignments(self._schedule, subdepartment, day))
        self.canvas.set_month(self._anchor, by_day, headcount)

    def _on_chip_clicked(self, day: date) -> None:
        subdepartment = self._subdepartment
        if not subdepartment:
            return
        current_id = self._assignments.get(day)
        current = next((t for t in self._templates if t.id == current_id), None)
        dialog = _AssignTemplateDialog(self._templates, current, self)
        if dialog.exec() != QDialog.Accepted:
            return
        chosen_name = dialog.chosen_name()
        if chosen_name == _NO_TEMPLATE:
            self._repository.delete_template_assignment(subdepartment, day)
        else:
            template = next((t for t in self._templates if t.name == chosen_name), None)
            if template is None:
                return
            self._repository.save_template_assignment(
                TemplateAssignment(subdepartment=subdepartment, date=day, template_id=template.id)
            )
        self._after_change(subdepartment, [day])

    def _on_remove_clicked(self, day: date) -> None:
        subdepartment = self._subdepartment
        if not subdepartment:
            return
        self._repository.delete_template_assignment(subdepartment, day)
        self._after_change(subdepartment, [day])

    def _on_template_dropped(self, day: date, template_id: str, source: date | None, copy: bool) -> None:
        subdepartment = self._subdepartment
        if not subdepartment or template_id not in {t.id for t in self._templates}:
            return
        if source == day:
            return
        self._repository.save_template_assignment(
            TemplateAssignment(subdepartment=subdepartment, date=day, template_id=template_id)
        )
        changed_days = [day]
        if source is not None and not copy:
            self._repository.delete_template_assignment(subdepartment, source)
            changed_days.append(source)
        self._after_change(subdepartment, changed_days)

    def _after_change(self, subdepartment: str, days: list[date]) -> None:
        """Shifts already on those days take the new template's times."""
        if self._schedule is not None:
            for day in days:
                retime_day(self._schedule, self._repository, subdepartment, day)
        self._render()
        if self._on_change:
            self._on_change()


# --- Year -------------------------------------------------------------------


class _MiniMonth(QWidget):
    """One month of the Year view, painted. Days are plain numbers — no
    background behind them. Only today gets a filled accent circle, sized
    to fit inside its own cell so neighbours never overlap. A day with a
    template gets a short colored bar under its number."""

    month_clicked = Signal(date)
    day_clicked = Signal(date)

    _PAD = 12
    _TITLE_HEIGHT = 26
    _HEAD_HEIGHT = 18
    _WEEK_COL_WIDTH = 24

    def __init__(self, accent_hex: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._accent_hex = accent_hex
        self._first = date.today().replace(month=1, day=1)
        self._assigned: dict[date, tuple[str, str]] = {}  # date -> (hex color, template name)
        self._hover: int | str | None = None  # day index, or "title"
        self.setMouseTracking(True)
        # Kept small for the same reason as _MonthCanvas's minimum.
        self.setMinimumSize(7 * 22 + self._WEEK_COL_WIDTH + 2 * self._PAD, 160)

    def set_month(self, first_of_month: date, assigned: dict[date, tuple[str, str]]) -> None:
        self._first = first_of_month
        self._assigned = assigned
        self.update()

    # --- geometry ---------------------------------------------------------

    def _day(self, index: int) -> date:
        return _sunday_on_or_before(self._first) + timedelta(days=index)

    def _in_month(self, day: date) -> bool:
        return day.month == self._first.month and day.year == self._first.year

    def _grid_origin(self) -> tuple[float, float, float, float]:
        left = self._PAD + self._WEEK_COL_WIDTH
        top = self._PAD + self._TITLE_HEIGHT + self._HEAD_HEIGHT
        cell_w = (self.width() - left - self._PAD) / 7
        cell_h = (self.height() - top - self._PAD) / _WEEKS
        return left, top, cell_w, cell_h

    def _cell_rect(self, index: int) -> QRectF:
        left, top, cell_w, cell_h = self._grid_origin()
        row, col = divmod(index, 7)
        return QRectF(left + col * cell_w, top + row * cell_h, cell_w, cell_h)

    def _title_rect(self) -> QRectF:
        metrics = QFontMetrics(_font(self.font(), 13, QFont.Bold))
        width = metrics.horizontalAdvance(calendar.month_name[self._first.month]) + 4
        return QRectF(self._PAD, self._PAD, width, self._TITLE_HEIGHT)

    def _hit(self, pos: QPointF) -> int | str | None:
        if self._title_rect().contains(pos):
            return "title"
        for index in range(_WEEKS * 7):
            if self._cell_rect(index).contains(pos):
                return index if self._in_month(self._day(index)) else None
        return None

    # --- painting ---------------------------------------------------------

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        card = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        painter.setPen(QPen(_color(COLORS["border_default"]), 1))
        painter.setBrush(_color(COLORS["bg_surface"]))
        painter.drawRoundedRect(card, 12, 12)

        # Title plus a hairline rule running to the right edge.
        title = self._title_rect()
        painter.setFont(_font(self.font(), 13, QFont.Bold))
        painter.setPen(_color(COLORS["accent"] if self._hover == "title" else COLORS["text_primary"]))
        painter.drawText(title, Qt.AlignLeft | Qt.AlignVCenter, calendar.month_name[self._first.month])
        rule_y = title.center().y()
        painter.setPen(QPen(_color(COLORS["border_default"]), 1))
        painter.drawLine(QPointF(title.right() + 8, rule_y), QPointF(self.width() - self._PAD, rule_y))

        left, top, cell_w, cell_h = self._grid_origin()
        painter.setFont(_font(self.font(), 10, QFont.DemiBold))
        painter.setPen(_color(COLORS["text_tertiary"]))
        for col, label in enumerate(_WEEKDAY_LABELS):
            head = QRectF(left + col * cell_w, top - self._HEAD_HEIGHT, cell_w, self._HEAD_HEIGHT)
            painter.drawText(head, Qt.AlignCenter, label[0])
        painter.setFont(_font(self.font(), 10, QFont.Bold))
        for week in range(_WEEKS):
            gutter = QRectF(self._PAD, top + week * cell_h, self._WEEK_COL_WIDTH, cell_h)
            painter.drawText(gutter, Qt.AlignLeft | Qt.AlignVCenter, str(self._day(week * 7).isocalendar()[1]))

        today = date.today()
        day_font = _font(self.font(), 11)
        bold_day_font = _font(self.font(), 11, QFont.Bold)
        # One diameter for every circle, capped by the smaller cell side, so
        # a circle can never reach into the next cell.
        diameter = min(cell_w, cell_h, 24.0) - 2
        for index in range(_WEEKS * 7):
            day = self._day(index)
            cell = self._cell_rect(index)
            circle = QRectF(
                cell.center().x() - diameter / 2, cell.center().y() - diameter / 2, diameter, diameter
            )
            in_month = self._in_month(day)
            assigned = self._assigned.get(day) if in_month else None
            if not in_month:
                painter.setFont(day_font)
                painter.setPen(_color(COLORS["text_tertiary"], 0.45))
                painter.drawText(circle, Qt.AlignCenter, str(day.day))
                continue
            if day == today:
                painter.setPen(Qt.NoPen)
                painter.setBrush(_color(self._accent_hex))
                painter.drawEllipse(circle)
                painter.setFont(bold_day_font)
                painter.setPen(_color(COLORS["accent_on"]))
            else:
                if self._hover == index:
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(_color(COLORS["bg_hover"]))
                    painter.drawEllipse(circle)
                painter.setFont(bold_day_font if assigned else day_font)
                painter.setPen(_color(COLORS["text_primary"] if assigned else COLORS["text_secondary"]))
            painter.drawText(circle, Qt.AlignCenter, str(day.day))
            if assigned is not None:
                bar = QRectF(cell.center().x() - 6, circle.bottom() + 1, 12, 2.5)
                painter.setPen(Qt.NoPen)
                painter.setBrush(_color(assigned[0]))
                painter.drawRoundedRect(bar, 1.25, 1.25)
        painter.end()

    # --- mouse --------------------------------------------------------------

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        hit = self._hit(event.position())
        if hit != self._hover:
            self._hover = hit
            self.setCursor(Qt.PointingHandCursor if hit is not None else Qt.ArrowCursor)
            self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = None
        self.setCursor(Qt.ArrowCursor)
        self.update()
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.LeftButton:
            return
        hit = self._hit(event.position())
        if hit == "title":
            self.month_clicked.emit(self._first)
        elif isinstance(hit, int):
            self.day_clicked.emit(self._day(hit))

    def event(self, event) -> bool:
        if event.type() == QEvent.ToolTip:
            hit = self._hit(QPointF(event.pos()))
            if hit == "title":
                QToolTip.showText(event.globalPos(), "Open this month", self)
            elif isinstance(hit, int) and self._day(hit) in self._assigned:
                QToolTip.showText(event.globalPos(), self._assigned[self._day(hit)][1], self)
            else:
                QToolTip.hideText()
            return True
        return super().event(event)


class YearGridView(QWidget):
    month_requested = Signal(date)
    day_requested = Signal(date)

    def __init__(
        self, repository: Repository, accent_hex: str | None = None, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._repository = repository
        self._year = date.today().year

        prev_button = QPushButton("<")
        prev_button.setFixedWidth(32)
        prev_button.clicked.connect(lambda: self._step(-1))
        next_button = QPushButton(">")
        next_button.setFixedWidth(32)
        next_button.clicked.connect(lambda: self._step(1))
        prev_button.setToolTip("Previous year")
        next_button.setToolTip("Next year")
        self.year_label = QLabel()
        self.year_label.setStyleSheet("font-weight: 600; font-size: 14px;")
        self._subdepartment = ""

        # Shown by the Schedule page in its top row.
        self.period_controls = QWidget()
        nav_row = QHBoxLayout(self.period_controls)
        nav_row.setContentsMargins(0, 0, 0, 0)
        nav_row.addWidget(prev_button)
        nav_row.addWidget(self.year_label)
        nav_row.addWidget(next_button)

        # Twelve painted months, built once; a render only hands them data.
        grid = QGridLayout()
        grid.setSpacing(12)
        self._months: list[_MiniMonth] = []
        for index in range(12):
            mini = _MiniMonth(accent_hex or COLORS["accent"])
            mini.month_clicked.connect(self.month_requested.emit)
            mini.day_clicked.connect(self.day_requested.emit)
            grid.addWidget(mini, index // 4, index % 4)
            self._months.append(mini)

        layout = QVBoxLayout(self)
        layout.addLayout(grid, stretch=1)
        self.year_label.setText(str(self._year))

    def set_subdepartment(self, subdepartment: str) -> None:
        self._subdepartment = subdepartment
        self._render()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._render()

    def _step(self, delta_years: int) -> None:
        self._year += delta_years
        self._render()

    def _render(self) -> None:
        self.year_label.setText(str(self._year))
        if not self.isVisible():
            return

        subdepartment = self._subdepartment
        assigned: dict[date, tuple[str, str]] = {}
        if subdepartment:
            templates_by_id = {t.id: t for t in self._repository.load_templates(subdepartment)}
            year_start = date(self._year, 1, 1)
            year_end = date(self._year, 12, 31)
            for ta in self._repository.load_template_assignments_range(subdepartment, year_start, year_end):
                template = templates_by_id.get(ta.template_id)
                if template is not None:
                    assigned[ta.date] = (_template_hex(template), template.name)

        for index, mini in enumerate(self._months):
            mini.set_month(date(self._year, index + 1, 1), assigned)
