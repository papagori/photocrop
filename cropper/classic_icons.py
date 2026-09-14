"""Original low-color pixel icons used exclusively by the Classic theme."""
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QIcon, QImage, QPainter, QPen, QPixmap, QPolygon


BLACK = QColor('#000000')
WHITE = QColor('#ffffff')
GRAY = QColor('#808080')
SILVER = QColor('#c0c0c0')
NAVY = QColor('#000080')
BLUE = QColor('#0000aa')
CYAN = QColor('#00a8a8')
GREEN = QColor('#008000')
LIME = QColor('#00aa00')
YELLOW = QColor('#ffff00')
GOLD = QColor('#d6a500')
RED = QColor('#aa0000')


def _rect(painter, color, x, y, width, height):
    painter.fillRect(x, y, width, height, color)


def _outline(painter, color, x, y, width, height):
    painter.setPen(QPen(color, 1))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRect(x, y, width - 1, height - 1)


def _folder(p):
    _rect(p, BLACK, 1, 4, 14, 10); _rect(p, GOLD, 2, 5, 12, 8)
    _rect(p, BLACK, 2, 2, 7, 4); _rect(p, YELLOW, 3, 3, 5, 3)
    _rect(p, YELLOW, 3, 6, 10, 2); _rect(p, QColor('#806000'), 2, 12, 12, 1)


def _trash(p):
    _rect(p, BLACK, 4, 3, 8, 2); _rect(p, WHITE, 5, 2, 6, 1)
    _rect(p, BLACK, 3, 5, 10, 9); _rect(p, SILVER, 4, 6, 8, 7)
    _rect(p, WHITE, 5, 6, 1, 6); _rect(p, GRAY, 10, 6, 1, 6)
    _rect(p, BLACK, 6, 1, 4, 1)


def _image(p):
    _rect(p, BLACK, 1, 1, 14, 14); _rect(p, WHITE, 2, 2, 12, 12)
    _rect(p, CYAN, 3, 3, 10, 7); _rect(p, YELLOW, 10, 4, 2, 2)
    p.setPen(QPen(GREEN, 1)); p.drawLine(3, 10, 7, 6); p.drawLine(7, 6, 11, 10); p.drawLine(8, 9, 13, 6)
    _rect(p, GREEN, 3, 10, 10, 3)


def _monitor(p):
    _rect(p, BLACK, 1, 1, 14, 11); _rect(p, SILVER, 2, 2, 12, 9)
    _rect(p, NAVY, 3, 3, 10, 7); _rect(p, CYAN, 4, 4, 8, 1)
    _rect(p, GRAY, 7, 12, 2, 2); _rect(p, BLACK, 4, 14, 8, 1)


def _format(p):
    _rect(p, BLACK, 2, 1, 12, 14); _rect(p, BLUE, 3, 2, 10, 12)
    _rect(p, WHITE, 5, 2, 6, 5); _rect(p, BLACK, 9, 2, 1, 4)
    _rect(p, SILVER, 5, 9, 7, 5); _rect(p, WHITE, 6, 10, 5, 3)


def _preview(p):
    _image(p)
    p.setPen(QPen(BLACK, 2)); p.drawEllipse(7, 7, 6, 6); p.drawLine(12, 12, 15, 15)
    p.setPen(QPen(WHITE, 1)); p.drawArc(8, 8, 4, 4, 40 * 16, 130 * 16)


def _process(p):
    p.setPen(QPen(BLACK, 1)); p.setBrush(GREEN)
    p.drawPolygon(QPolygon([QPoint(1, 6), QPoint(9, 6), QPoint(9, 2), QPoint(15, 8),
                            QPoint(9, 14), QPoint(9, 10), QPoint(1, 10)]))
    _rect(p, LIME, 3, 7, 8, 2); _rect(p, WHITE, 10, 5, 1, 1)


def _language(p):
    _rect(p, BLACK, 1, 1, 14, 14); _rect(p, BLUE, 2, 2, 12, 12)
    p.setPen(QPen(CYAN, 1)); p.drawEllipse(3, 2, 9, 12); p.drawLine(2, 7, 13, 7); p.drawLine(3, 4, 12, 4); p.drawLine(3, 10, 12, 10)
    p.setPen(QPen(WHITE, 1)); p.drawLine(7, 2, 7, 13)


def _theme(p):
    _monitor(p)
    _rect(p, RED, 4, 4, 3, 2); _rect(p, YELLOW, 7, 4, 3, 2); _rect(p, GREEN, 10, 4, 2, 2)
    _rect(p, WHITE, 4, 7, 8, 2)


DRAWERS = {
    'folder': _folder, 'trash': _trash, 'image': _image, 'monitor': _monitor,
    'format': _format, 'preview': _preview, 'process': _process,
    'language': _language, 'theme': _theme,
}


def classic_icon(name, size=16):
    """Return a crisp scalable QIcon without depending on shell resources."""
    image = QImage(16, 16, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
    DRAWERS[name](painter)
    painter.end()
    pixmap = QPixmap.fromImage(image)
    if size != 16:
        pixmap = pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                               Qt.TransformationMode.FastTransformation)
    return QIcon(pixmap)
