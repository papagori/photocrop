"""Centralized PhotoCrop theme definitions and reusable themed widgets."""
from PySide6.QtCore import QPoint, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap, QPolygon
from PySide6.QtWidgets import QCheckBox, QComboBox, QLabel


THEMES = ('dark', 'light', 'classic')

TOGGLE_COLORS = {
    'dark': {'off': '#475569', 'on': '#3b82f6', 'knob': '#f8fafc', 'text': '#e5e7eb'},
    'light': {'off': '#a8b1bd', 'on': '#2563eb', 'knob': '#ffffff', 'text': '#20242b'},
    'classic': {'off': '#808080', 'on': '#000080', 'knob': '#dfdfdf', 'text': '#000000'},
}


def normalize_theme(value):
    value = str(value or '').lower()
    return value if value in THEMES else 'dark'


class ToggleSwitch(QCheckBox):
    """Compact, non-animated switch that follows the selected application theme."""

    def __init__(self, text='', parent=None):
        super().__init__(text, parent)
        self.theme_name = 'dark'
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(24)

    def set_theme(self, theme_name):
        self.theme_name = normalize_theme(theme_name)
        self.update()

    def sizeHint(self):
        width = 50 + self.fontMetrics().horizontalAdvance(self.text())
        return QSize(width, max(24, self.fontMetrics().height() + 6))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, self.theme_name != 'classic')
        colors = TOGGLE_COLORS[self.theme_name]
        enabled = self.isEnabled()
        opacity = 1.0 if enabled else 0.48
        painter.setOpacity(opacity)
        y = (self.height() - 20) / 2
        track = QRectF(1, y, 38, 20)
        radius = 10 if self.theme_name != 'classic' else 1
        painter.setPen(QPen(QColor('#64748b' if self.theme_name != 'classic' else '#000000'), 1))
        painter.setBrush(QColor(colors['on'] if self.isChecked() else colors['off']))
        painter.drawRoundedRect(track, radius, radius)
        knob_x = 20 if self.isChecked() else 3
        knob = QRectF(knob_x, y + 3, 14, 14)
        painter.setPen(QPen(QColor('#334155' if self.theme_name != 'classic' else '#808080'), 0.7))
        painter.setBrush(QColor(colors['knob']))
        painter.drawRoundedRect(knob, 7 if self.theme_name != 'classic' else 0, 7 if self.theme_name != 'classic' else 0)
        painter.setOpacity(opacity)
        painter.setPen(QColor(colors['text']))
        painter.drawText(47, 0, self.width() - 47, self.height(),
                         Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self.text())
        if self.hasFocus():
            painter.setPen(QPen(QColor(colors['on']), 1, Qt.PenStyle.DotLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self.rect().adjusted(0, 0, -1, -1))


class LinkLabel(QLabel):
    """Keyboard-accessible label that opens a link through its owner."""
    clicked = Signal()

    def __init__(self, text='', parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.clicked.emit()
        else:
            super().keyPressEvent(event)


class ThemedComboBox(QComboBox):
    """QComboBox with a consistently visible arrow in every QSS theme."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme_name = 'dark'
        self.arrow = QLabel(self)
        self.arrow.setObjectName('comboArrow')
        self.arrow.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._update_arrow()

    def set_theme(self, theme_name):
        self.theme_name = normalize_theme(theme_name)
        self._update_arrow()

    def _update_arrow(self):
        pixmap = QPixmap(12, 8)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, self.theme_name != 'classic')
        if not self.isEnabled():
            color = QColor('#808080')
        else:
            color = QColor({'dark': '#f1f5f9', 'light': '#1f2937', 'classic': '#000000'}[
                self.theme_name])
        points = [QPoint(1, 1), QPoint(11, 1), QPoint(6, 7)]
        painter.setPen(QPen(color, 1))
        painter.setBrush(color)
        painter.drawPolygon(QPolygon(points))
        painter.end()
        self.arrow.setPixmap(pixmap)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.arrow.setGeometry(self.width() - 27, 0, 26, self.height())
        self.arrow.raise_()


_COMMON = '''
QWidget { font-size: 13px; }
ToggleSwitch { background: transparent; }
QLabel#title { font-size: 27px; font-weight: 700; }
QLabel#versionBadge { border-radius: 9px; font-size: 11px; font-weight: 600; padding: 3px 8px; }
QLabel#sectionTitle { font-size: 15px; font-weight: 600; }
QLabel#stepLabel { font-size: 11px; font-weight: 700; }
QLabel#previewDetails { font-family: "Cascadia Mono", "Consolas", monospace; font-size: 12px; }
QFrame#settingsPanel, QFrame#previewPanel, QFrame#footer { border-radius: 10px; }
QFrame#settingsPanel QLabel, QFrame#previewPanel QLabel, QFrame#footer QLabel { background: transparent; border: none; }
QFrame#previewCanvas { border-radius: 6px; }
QFrame#dropArea { border-radius: 10px; }
QFrame#dropArea QLabel { background: transparent; border: none; }
QLabel#dropTitle { font-size: 19px; font-weight: 600; }
QPushButton { border-radius: 7px; min-height: 20px; padding: 8px 20px; }
QPushButton#primary { font-size: 14px; font-weight: 700; }
QTableWidget, QPlainTextEdit { border-radius: 7px; }
QHeaderView::section { border: none; padding: 8px; font-weight: 600; }
QTableWidget::item { padding: 6px; }
QProgressBar { border: none; border-radius: 4px; text-align: center; min-height: 17px; }
QProgressBar::chunk { border-radius: 4px; }
QMenu { padding: 6px; }
QMenu::item { padding: 8px 24px; }
QComboBox { border-radius: 6px; min-height: 26px; padding: 6px 34px 6px 10px; }
QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: top right; width: 28px; }
QComboBox::down-arrow { width: 10px; height: 7px; }
QComboBox QAbstractItemView { min-width: 350px; padding: 5px; outline: 0; }
QLabel#footerLink { font-size: 12px; }
QLabel#comboArrow { background: transparent; border: none; }
'''

_DARK = '''
QWidget { background: #11151b; color: #e7eaf0; font-family: "Segoe UI Variable Text", "Segoe UI", "Yu Gothic UI", "Meiryo UI", sans-serif; }
QLabel#title { color: #f8fafc; }
QLabel#versionBadge { background: #18385d; color: #9dcbff; border: 1px solid #31577f; }
QLabel#sectionTitle { color: #f1f5f9; }
QLabel#stepLabel { color: #78c7ff; }
QLabel#muted { color: #98a6b8; }
QLabel#previewDetails { color: #cbd5e1; }
QFrame#settingsPanel, QFrame#previewPanel { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #1b2430, stop:1 #161e29); border: 1px solid #2c3a4d; }
QFrame#footer { background: #151b23; border: 1px solid #263241; }
QFrame#previewCanvas { background: #090d13; border: 1px solid #2a394d; }
QFrame#dropArea { background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #172333, stop:1 #14202d); border: 1px dashed #58728f; }
QFrame#dropArea:hover, QFrame#dropArea:focus { background: #1a2b3e; border-color: #60a5fa; }
QFrame#dropArea[dragActive="true"] { background: #193958; border: 2px solid #60a5fa; }
QLabel#dropTitle { color: #f8fafc; }
QPushButton { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #2b394b, stop:1 #202c3b); border: 1px solid #42546b; }
QPushButton:hover { background: #31445b; border-color: #607791; }
QPushButton:focus { border-color: #60a5fa; }
QPushButton#primary { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #3478e5, stop:1 #2162c7); border-color: #4a8df0; color: white; }
QPushButton#primary:hover { background: #3478f6; }
QPushButton:disabled { background: #1b2532; color: #64748b; border-color: #2a3544; }
QPushButton#primary:disabled { background: #1b2532; color: #64748b; border-color: #2a3544; }
QTableWidget, QPlainTextEdit { background: #141b25; alternate-background-color: #192331; border: 1px solid #2c3a4d; gridline-color: #273547; selection-background-color: #245fbd; selection-color: white; }
QHeaderView::section { background: #202c3b; color: #cbd5e1; border-bottom: 1px solid #35465c; }
QProgressBar { background: #263244; color: #e2e8f0; }
QProgressBar::chunk { background: #3b82f6; }
QMenu, QComboBox QAbstractItemView { background: #1b2735; color: #f3f6fa; border: 1px solid #66809e; selection-background-color: #2563eb; selection-color: white; }
QMenu::item:selected, QComboBox QAbstractItemView::item:selected { background: #2563eb; color: white; }
QComboBox { background: #1c2938; color: #f8fafc; border: 1px solid #58718e; selection-background-color: #2563eb; selection-color: white; }
QComboBox::drop-down { background: #2a3b50; border-left: 1px solid #58718e; border-top-right-radius: 5px; border-bottom-right-radius: 5px; }
QComboBox:hover { background: #223247; border-color: #7ba3cf; }
QComboBox:hover::drop-down { background: #344b65; }
QComboBox:focus, QComboBox:on { background: #213147; border: 2px solid #4d9cff; }
QComboBox:on::drop-down { background: #315274; border-left-color: #4d9cff; }
QComboBox:disabled { color: #718096; background: #1a2330; border-color: #2b394d; }
QLabel#footerLink { color: #7cbcff; }
'''

_LIGHT = '''
QWidget { background: #f5f6f8; color: #20242b; font-family: "Segoe UI Variable Text", "Segoe UI", "Yu Gothic UI", "Meiryo UI", sans-serif; }
QLabel#title { color: #171a1f; }
QLabel#versionBadge { background: #e6f1ff; color: #1859a8; border: 1px solid #aacbf2; }
QLabel#sectionTitle { color: #20242b; }
QLabel#stepLabel { color: #1769c2; }
QLabel#muted { color: #657184; }
QLabel#previewDetails { color: #3f4a59; }
QFrame#settingsPanel, QFrame#previewPanel { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #ffffff, stop:1 #f0f2f5); border: 1px solid #d4d9e0; }
QFrame#footer { background: #ffffff; border: 1px solid #d9dde3; }
QFrame#previewCanvas { background: #e8ebef; border: 1px solid #c9cfd8; }
QFrame#dropArea { background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #ffffff, stop:1 #edf4fb); border: 1px dashed #7d9dbf; }
QFrame#dropArea:hover, QFrame#dropArea:focus { background: #e9f3ff; border-color: #2878cc; }
QFrame#dropArea[dragActive="true"] { background: #dceeff; border: 2px solid #2878cc; }
QLabel#dropTitle { color: #20242b; }
QPushButton { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #ffffff, stop:1 #e8ebef); border: 1px solid #bfc6cf; }
QPushButton:hover { background: #eef5ff; border-color: #7aa7d8; }
QPushButton:focus { border-color: #2878cc; }
QPushButton#primary { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #3686df, stop:1 #1767bd); border-color: #1763ad; color: white; }
QPushButton#primary:hover { background: #287bd2; }
QPushButton:disabled { background: #eceff2; color: #9ba3ad; border-color: #d5d9de; }
QPushButton#primary:disabled { background: #eceff2; color: #9ba3ad; border-color: #d5d9de; }
QTableWidget, QPlainTextEdit { background: #ffffff; alternate-background-color: #f4f6f8; border: 1px solid #d0d5dc; gridline-color: #e0e4e9; selection-background-color: #2d72c4; selection-color: white; }
QHeaderView::section { background: #e9edf2; color: #303741; border-bottom: 1px solid #cbd1d9; }
QProgressBar { background: #dde2e8; color: #20242b; }
QProgressBar::chunk { background: #2878cc; }
QMenu, QComboBox QAbstractItemView { background: #ffffff; color: #161b22; border: 1px solid #8d9bad; selection-background-color: #2878cc; selection-color: white; }
QMenu::item:selected, QComboBox QAbstractItemView::item:selected { background: #2878cc; color: white; }
QComboBox { background: #ffffff; color: #151a21; border: 1px solid #8795a8; selection-background-color: #2878cc; selection-color: white; }
QComboBox::drop-down { background: #e5ebf2; border-left: 1px solid #a3afbd; border-top-right-radius: 5px; border-bottom-right-radius: 5px; }
QComboBox:hover { background: #f9fcff; border-color: #3e82c8; }
QComboBox:hover::drop-down { background: #d8e8f8; }
QComboBox:focus, QComboBox:on { background: #ffffff; border: 2px solid #2878cc; }
QComboBox:on::drop-down { background: #cee3f7; border-left-color: #2878cc; }
QComboBox:disabled { color: #9ba3ad; background: #eceff2; border-color: #d5d9de; }
QLabel#footerLink { color: #1769c2; }
'''

_CLASSIC = '''
QWidget { background: #c0c0c0; color: #000000; font-family: "Tahoma", "Yu Gothic UI", "Meiryo UI", sans-serif; font-size: 12px; }
QLabel#title { color: #000080; font-size: 25px; }
QLabel#versionBadge { background: #c0c0c0; color: #000000; border: 2px outset #ffffff; border-radius: 0px; }
QLabel#sectionTitle { color: #000000; }
QLabel#stepLabel { color: #000080; }
QLabel#muted, QLabel#previewDetails { color: #333333; }
QFrame#settingsPanel, QFrame#previewPanel, QFrame#footer { background: #c0c0c0; border: 2px outset #ffffff; border-radius: 0px; }
QFrame#previewCanvas { background: #808080; border: 2px inset #ffffff; border-radius: 0px; }
QFrame#dropArea { background: #d4d0c8; border: 2px inset #ffffff; border-radius: 0px; }
QFrame#dropArea:hover, QFrame#dropArea:focus, QFrame#dropArea[dragActive="true"] { background: #ffffff; border: 2px inset #ffffff; }
QLabel#dropTitle { color: #000080; }
QPushButton { background: #c0c0c0; border: 2px outset #ffffff; border-radius: 0px; }
QPushButton:pressed { border: 2px inset #ffffff; }
QPushButton:focus { border: 2px solid #000000; }
QPushButton#primary { background: #000080; color: #ffffff; border: 2px outset #ffffff; }
QPushButton:disabled { color: #808080; background: #c0c0c0; }
QPushButton#primary:disabled { color: #808080; background: #c0c0c0; border: 2px outset #ffffff; }
QTableWidget, QPlainTextEdit { background: #ffffff; alternate-background-color: #eeeeee; border: 2px inset #ffffff; border-radius: 0px; gridline-color: #808080; selection-background-color: #000080; selection-color: #ffffff; }
QHeaderView::section { background: #c0c0c0; color: #000000; border: 2px outset #ffffff; }
QProgressBar { background: #ffffff; color: #000000; border: 2px inset #ffffff; border-radius: 0px; }
QProgressBar::chunk { background: #000080; border-radius: 0px; }
QMenu, QComboBox QAbstractItemView { background: #c0c0c0; color: #000000; border: 2px outset #ffffff; selection-background-color: #000080; selection-color: #ffffff; }
QMenu::item:selected, QComboBox QAbstractItemView::item:selected { background: #000080; color: #ffffff; }
QComboBox { background: #ffffff; color: #000000; border: 2px inset #ffffff; border-radius: 0px; min-height: 24px; padding: 5px 32px 5px 8px; selection-background-color: #000080; selection-color: #ffffff; }
QComboBox::drop-down { background: #c0c0c0; border-left: 2px outset #ffffff; width: 26px; }
QComboBox:hover { background: #ffffe1; }
QComboBox:hover::drop-down { background: #d4d0c8; }
QComboBox:focus { border: 2px solid #000000; }
QComboBox:on { background: #ffffff; border: 2px inset #808080; }
QComboBox:on::drop-down { background: #a0a0a0; border-left: 2px inset #ffffff; }
QComboBox:disabled { color: #808080; background: #c0c0c0; }
QLabel#footerLink { color: #000080; text-decoration: underline; }
'''


def theme_stylesheet(theme_name, language='en'):
    theme_name = normalize_theme(theme_name)
    stylesheet = _COMMON + {'dark': _DARK, 'light': _LIGHT, 'classic': _CLASSIC}[theme_name]
    if language == 'ja':
        stylesheet += '\nQWidget { font-family: "Yu Gothic UI", "Meiryo UI", "Segoe UI", sans-serif; }\n'
    return stylesheet
