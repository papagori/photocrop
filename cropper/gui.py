"""Qt interface; discovery and image work run outside the GUI thread."""
from PIL import Image, ImageOps
from PIL.ImageQt import ImageQt
from PySide6.QtCore import QRectF, Qt, QThread, Signal
from PySide6.QtGui import QColor, QCursor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel,
    QMainWindow, QMenu, QPlainTextEdit, QProgressBar, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QHeaderView,
)

from .discovery import discover
from .geometry import crop_box, output_size
from .processing import process_image
from .resources import resource_path
from .settings import ASPECT_RATIOS, ProcessingOptions, presets_for_ratio
from .version import __version__


class Worker(QThread):
    discovered = Signal(object)
    progress = Signal(int, int)
    result = Signal(int, object)

    def __init__(self, paths, recursive=None, existing=(), parent=None, options=ProcessingOptions()):
        super().__init__(parent)
        self.paths, self.recursive, self.existing = paths, recursive, existing
        self.options = options

    def run(self):
        if self.recursive is not None:
            self.discovered.emit(discover(self.paths, self.recursive, self.existing))
        else:
            for index, path in enumerate(self.paths):
                self.progress.emit(index + 1, len(self.paths))
                self.result.emit(index, process_image(path, self.options))


class DropArea(QFrame):
    paths_added = Signal(list)
    clicked = Signal()

    def __init__(self):
        super().__init__()
        self.setObjectName('dropArea')
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName('Add files or folder')
        self.setMinimumHeight(116)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = QLabel('Drop files or folder here')
        title.setObjectName('dropTitle')
        hint = QLabel('or click here to add files or folder')
        hint.setObjectName('muted')
        for label in (title, hint):
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            layout.addWidget(label)

    def dragEnterEvent(self, event):
        if self.isEnabled() and any(url.isLocalFile() for url in event.mimeData().urls()):
            self.set_drag_active(True)
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self.set_drag_active(False)
        event.accept()

    def dropEvent(self, event):
        self.set_drag_active(False)
        self.paths_added.emit([url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()])
        event.acceptProposedAction()

    def set_drag_active(self, active):
        self.setProperty('dragActive', active)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.clicked.emit()
        else:
            super().keyPressEvent(event)


class PreviewCanvas(QFrame):
    """Paint an oriented thumbnail with only the cropped-away area darkened."""

    def __init__(self):
        super().__init__()
        self.pixmap = None
        self.source_size = None
        self.crop = None
        self.setMinimumSize(260, 130)
        self.setObjectName('previewCanvas')

    def set_preview(self, pixmap, source_size, crop):
        self.pixmap, self.source_size, self.crop = pixmap, source_size, crop
        self.update()

    def clear_preview(self):
        self.set_preview(None, None, None)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        if not self.pixmap or not self.source_size:
            painter.setPen(QColor('#718096'))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, 'Select an image to preview')
            return
        bounds = QRectF(self.rect().adjusted(10, 10, -10, -10))
        scaled = self.pixmap.size()
        scaled.scale(bounds.size().toSize(), Qt.AspectRatioMode.KeepAspectRatio)
        image_rect = QRectF(0, 0, scaled.width(), scaled.height())
        image_rect.moveCenter(bounds.center())
        painter.drawPixmap(image_rect.toRect(), self.pixmap)
        left, top, right, bottom = self.crop
        source_width, source_height = self.source_size
        scale_x = image_rect.width() / source_width
        scale_y = image_rect.height() / source_height
        crop_rect = QRectF(image_rect.left() + left * scale_x,
                           image_rect.top() + top * scale_y,
                           (right - left) * scale_x, (bottom - top) * scale_y)
        shade = QColor(0, 0, 0, 165)
        painter.fillRect(QRectF(image_rect.left(), image_rect.top(),
                                crop_rect.left() - image_rect.left(), image_rect.height()), shade)
        painter.fillRect(QRectF(crop_rect.right(), image_rect.top(),
                                image_rect.right() - crop_rect.right(), image_rect.height()), shade)
        painter.fillRect(QRectF(crop_rect.left(), image_rect.top(), crop_rect.width(),
                                crop_rect.top() - image_rect.top()), shade)
        painter.fillRect(QRectF(crop_rect.left(), crop_rect.bottom(), crop_rect.width(),
                                image_rect.bottom() - crop_rect.bottom()), shade)
        painter.setPen(QPen(QColor('#f8fafc'), 1.5))
        painter.drawRect(crop_rect)


class PreviewPanel(QFrame):
    def __init__(self):
        super().__init__()
        self.source_size = None
        self.pixmap = None
        self.setObjectName('previewPanel')
        self.setMinimumWidth(310)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        title = QLabel('4 · Preview')
        title.setObjectName('sectionTitle')
        self.canvas = PreviewCanvas()
        self.details = QLabel('Source: —\nCrop: —\nOutput: —')
        self.details.setObjectName('previewDetails')
        layout.addWidget(title)
        layout.addWidget(self.canvas, 1)
        layout.addWidget(self.details)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.paths = []
        self.worker = None
        self.busy = False
        self.skipped = self.processed = self.errors = 0
        self.scan_errors = 0
        self.setWindowTitle(f'PhotoCropV2 — {__version__}')
        icon_path = resource_path('assets/photocrop.ico')
        if icon_path.is_file():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.resize(1040, 800)
        self.setMinimumSize(860, 700)
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(26, 22, 26, 22)
        layout.setSpacing(12)
        header = QHBoxLayout()
        header.setSpacing(10)
        title = QLabel('PhotoCrop')
        title.setObjectName('title')
        version = QLabel(f'v{__version__}')
        version.setObjectName('versionBadge')
        header.addWidget(title)
        header.addWidget(version)
        header.addStretch()
        layout.addLayout(header)
        subtitle = QLabel('Centered crop · Automatic orientation · Maximum JPEG quality')
        subtitle.setObjectName('muted')
        layout.addWidget(subtitle)
        add_label = QLabel('1 · ADD IMAGES')
        add_label.setObjectName('stepLabel')
        layout.addWidget(add_label)
        self.drop = DropArea()
        self.drop.clicked.connect(self.choose_input)
        self.drop.paths_added.connect(self.add_paths)
        layout.addWidget(self.drop)
        self.recursive = QCheckBox('Include subfolders')
        self.recursive.setToolTip('Applies to folders added next. Output folders are excluded.')
        layout.addWidget(self.recursive)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(['Source image', 'Result'])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.currentCellChanged.connect(self.preview_selection_changed)
        content = QHBoxLayout()
        content.setSpacing(12)
        file_column = QVBoxLayout()
        file_column.setSpacing(8)
        file_title = QLabel('Selected files')
        file_title.setObjectName('sectionTitle')
        file_column.addWidget(file_title)
        file_column.addWidget(self.table, 1)
        content.addLayout(file_column, 3)
        self.preview = PreviewPanel()
        content.addWidget(self.preview, 2)
        settings = QHBoxLayout()
        settings.setContentsMargins(14, 12, 14, 12)
        settings.setSpacing(14)
        aspect_column = QVBoxLayout()
        aspect_column.setSpacing(6)
        aspect_label = QLabel('2 · Aspect Ratio')
        self.aspect = QComboBox()
        self.aspect.setAccessibleName('Aspect Ratio')
        for label, ratio in ASPECT_RATIOS.items():
            self.aspect.addItem(label, ratio)
        self.aspect.setCurrentText('4:3')
        aspect_label.setBuddy(self.aspect)
        aspect_column.addWidget(aspect_label)
        aspect_column.addWidget(self.aspect)
        size_column = QVBoxLayout()
        size_column.setSpacing(6)
        size_label = QLabel('3 · Output Size')
        self.output_size = QComboBox()
        self.output_size.setAccessibleName('Output Size')
        self.output_size.setMaxVisibleItems(10)
        size_label.setBuddy(self.output_size)
        size_column.addWidget(size_label)
        size_column.addWidget(self.output_size)
        settings.addLayout(aspect_column, 2)
        settings.addLayout(size_column, 3)
        option_column = QVBoxLayout()
        self.upscaling = QCheckBox('Allow Upscaling')
        self.upscaling.setToolTip('Allow enlargement beyond the cropped image resolution.')
        option_column.addStretch()
        option_column.addWidget(self.upscaling)
        settings.addLayout(option_column, 2)
        settings_panel = QFrame()
        settings_panel.setObjectName('settingsPanel')
        settings_panel.setLayout(settings)
        layout.addWidget(settings_panel)
        self.summary = QLabel()
        self.summary.setObjectName('muted')
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        layout.addLayout(content, 1)
        self.output_size.currentIndexChanged.connect(self.output_changed)
        self.aspect.currentIndexChanged.connect(self.aspect_changed)
        self.upscaling.toggled.connect(self.settings_changed)
        self.aspect_changed()
        actions = QHBoxLayout()
        self.clear = QPushButton('Clear')
        self.clear.setMinimumWidth(96)
        self.clear.clicked.connect(self.clear_all)
        self.process = QPushButton('Process')
        self.process.setObjectName('primary')
        self.process.setMinimumSize(150, 42)
        self.process.clicked.connect(self.start_processing)
        self.process.setEnabled(False)
        actions.addWidget(self.clear)
        actions.addStretch()
        actions.addWidget(self.process)
        layout.addLayout(actions)
        self.progress = QProgressBar()
        self.progress.setValue(0)
        layout.addWidget(self.progress)
        self.status = QLabel('Ready')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(105)
        self.log.setPlaceholderText('Output paths and error details appear here.')
        layout.addWidget(self.log)
        self.setStyleSheet('''
            QWidget { background: #0f172a; color: #e5e7eb; font-family: "Segoe UI"; font-size: 13px; }
            QLabel#title { font-size: 27px; font-weight: 700; color: #f8fafc; }
            QLabel#versionBadge { background: #1e3a5f; color: #93c5fd; border-radius: 9px;
                                  font-size: 11px; font-weight: 600; padding: 3px 8px; }
            QLabel#sectionTitle { font-size: 15px; font-weight: 600; color: #f1f5f9; }
            QLabel#stepLabel { color: #7dd3fc; font-size: 11px; font-weight: 700; }
            QLabel#muted { color: #94a3b8; }
            QLabel#previewDetails { color: #cbd5e1; font-family: "Cascadia Mono", "Consolas";
                                    font-size: 12px; line-height: 1.5; }
            QFrame#settingsPanel, QFrame#previewPanel { background: #172033;
                border: 1px solid #2b3b52; border-radius: 10px; }
            QFrame#settingsPanel QLabel, QFrame#settingsPanel QCheckBox { background: transparent; }
            QFrame#previewPanel QLabel { background: transparent; border: none; }
            QFrame#previewCanvas { background: #080f1d; border: 1px solid #26364d; border-radius: 6px; }
            QFrame#dropArea { background: #152238; border: 1px dashed #55708f; border-radius: 10px; }
            QFrame#dropArea:hover, QFrame#dropArea:focus { background: #182943; border-color: #60a5fa; }
            QFrame#dropArea[dragActive="true"] { background: #193457; border: 2px solid #60a5fa; }
            QFrame#dropArea QLabel { background: transparent; border: none; }
            QLabel#dropTitle { color: #f8fafc; font-size: 19px; font-weight: 600; }
            QPushButton { background: #233248; border: 1px solid #3a4b63; border-radius: 7px;
                          min-height: 20px; padding: 8px 20px; }
            QPushButton:hover { background: #2d405b; border-color: #536a89; }
            QPushButton:focus { border-color: #60a5fa; }
            QPushButton#primary { background: #2563eb; border-color: #3b82f6; color: white;
                                  font-size: 14px; font-weight: 700; }
            QPushButton#primary:hover { background: #3478f6; border-color: #60a5fa; }
            QPushButton:disabled { background: #1b2638; color: #64748b; border-color: #273449; }
            QTableWidget, QPlainTextEdit { background: #151f31; alternate-background-color: #182438;
                border: 1px solid #2b3b52; border-radius: 7px; gridline-color: #26364d;
                selection-background-color: #1d4ed8; selection-color: white; }
            QHeaderView::section { background: #1e2c42; color: #cbd5e1; border: none;
                                   border-bottom: 1px solid #33445d; padding: 8px; font-weight: 600; }
            QTableWidget::item { padding: 6px; }
            QTableWidget::item:selected { background: #1d4ed8; color: white; }
            QProgressBar { border: none; border-radius: 4px; background: #243249;
                           color: #e2e8f0; text-align: center; min-height: 17px; }
            QProgressBar::chunk { background: #3b82f6; border-radius: 4px; }
            QMenu { background: #223047; border: 1px solid #3b4d66; padding: 6px; }
            QMenu::item { padding: 8px 24px; }
            QMenu::item:selected { background: #2563eb; }
            QComboBox { background: #202d43; border: 1px solid #465a74; border-radius: 6px;
                        min-height: 22px; padding: 7px 10px; }
            QComboBox:hover, QComboBox:focus { border-color: #60a5fa; }
            QComboBox:disabled { color: #718096; background: #1a2537; border-color: #2b394d; }
            QComboBox QAbstractItemView { background: #223047; border: 1px solid #465a74;
                selection-background-color: #2563eb; min-width: 350px; padding: 4px; }
            QCheckBox { spacing: 8px; }
            QCheckBox::indicator { width: 17px; height: 17px; }
        ''')

    def current_options(self):
        return ProcessingOptions(self.aspect.currentData(), self.output_size.currentData(),
                                 self.upscaling.isChecked())

    def aspect_changed(self):
        current = self.output_size.currentData()
        preferred = current.key if current and current.key in ('maximum', 'original') else None
        self.populate_output_sizes(preferred)

    def populate_output_sizes(self, preferred_key=None):
        portrait = bool(self.preview.source_size and self.preview.source_size[1] > self.preview.source_size[0])
        self.output_size.blockSignals(True)
        self.output_size.clear()
        selected_index = 0
        for index, preset in enumerate(presets_for_ratio(self.aspect.currentText())):
            label = preset.label
            if portrait and preset.dimensions and preset.dimensions[0] != preset.dimensions[1]:
                label = f'{preset.dimensions[1]} × {preset.dimensions[0]}'
            self.output_size.addItem(label, preset)
            if preset.key == preferred_key:
                selected_index = index
        self.output_size.setCurrentIndex(selected_index)
        self.output_size.blockSignals(False)
        self.output_changed()

    def output_changed(self):
        preset = self.output_size.currentData()
        if preset is None:
            return
        self.aspect.setEnabled(not self.busy)
        self.aspect.setToolTip('Automatically reversed for portrait images.')
        can_resize = preset.dimensions is not None or preset.long_edge is not None
        self.upscaling.setEnabled(not self.busy and can_resize)
        self.settings_changed()

    def settings_changed(self):
        preset = self.output_size.currentData()
        if preset is None:
            return
        parts = [self.aspect.currentText(), preset.label]
        if preset.dimensions is not None or preset.long_edge is not None:
            parts.append('Upscaling allowed' if self.upscaling.isChecked() else 'No upscaling')
        parts.append('JPEG maximum quality')
        self.refresh_preview()
        self.summary.setText(' · '.join(parts))

    def preview_selection_changed(self, current_row, _current_column, _previous_row, _previous_column):
        self.load_preview(current_row)

    def load_preview(self, row):
        if row < 0 or row >= len(self.paths):
            self.preview.canvas.clear_preview()
            self.preview.source_size = None
            self.preview.details.setText('Source: —\nCrop: —\nOutput: —')
            return
        try:
            with Image.open(self.paths[row]) as source:
                oriented = ImageOps.exif_transpose(source)
                oriented.load()
                source_size = oriented.size
                thumbnail = oriented.copy()
                thumbnail.thumbnail((1200, 900), Image.Resampling.LANCZOS)
                pixmap = QPixmap.fromImage(ImageQt(thumbnail.convert('RGBA'))).copy()
            previous_portrait = bool(self.preview.source_size and self.preview.source_size[1] > self.preview.source_size[0])
            self.preview.source_size = source_size
            self.preview.pixmap = pixmap
            current_portrait = source_size[1] > source_size[0]
            if previous_portrait != current_portrait:
                preset = self.output_size.currentData()
                self.populate_output_sizes(preset.key if preset else None)
            else:
                self.refresh_preview()
        except Exception as exc:
            self.preview.canvas.clear_preview()
            self.preview.source_size = None
            self.preview.details.setText(f'Preview unavailable\n{type(exc).__name__}: {exc}')

    def refresh_preview(self):
        source_size = self.preview.source_size
        if not source_size or self.output_size.currentData() is None:
            return
        box = crop_box(*source_size, self.aspect.currentData())
        cropped_size = box[2] - box[0], box[3] - box[1]
        final_size, blocked = output_size(
            cropped_size, self.current_options(), portrait=source_size[1] > source_size[0])
        self.preview.canvas.set_preview(self.preview.pixmap, source_size, box)
        suffix = ' (upscaling avoided)' if blocked else ''
        self.preview.details.setText(
            f'Source: {source_size[0]} × {source_size[1]}\n'
            f'Crop: {cropped_size[0]} × {cropped_size[1]}\n'
            f'Output: {final_size[0]} × {final_size[1]}{suffix}')

    def choose_input(self):
        menu = QMenu(self)
        files = menu.addAction('Add files…')
        folder = menu.addAction('Add folder…')
        choice = menu.exec(QCursor.pos())
        if choice == files:
            paths, _ = QFileDialog.getOpenFileNames(self, 'Add images', '',
                'Images (*.jpg *.jpeg *.png *.tif *.tiff *.webp);;All files (*)')
            self.add_paths(paths)
        elif choice == folder:
            path = QFileDialog.getExistingDirectory(self, 'Add folder')
            if path:
                self.add_paths([path])

    def set_busy(self, value):
        self.busy = value
        for widget in (self.drop, self.recursive, self.clear, self.output_size):
            widget.setEnabled(not value)
        self.output_changed()
        self.process.setEnabled(not value and bool(self.paths))

    def add_paths(self, paths):
        if self.busy or not paths:
            return
        self.set_busy(True)
        self.status.setText('Looking for images…')
        self.progress.setRange(0, 0)
        self.worker = Worker(list(paths), self.recursive.isChecked(), tuple(self.paths), self)
        self.worker.discovered.connect(self.on_discovered)
        self.worker.finished.connect(self.finish_scan)
        self.worker.start()

    def on_discovered(self, result):
        self.skipped += result.skipped
        self.scan_errors += len(result.errors)
        for path in result.files:
            row = self.table.rowCount()
            self.table.insertRow(row)
            item = QTableWidgetItem(str(path))
            item.setToolTip(str(path))
            self.table.setItem(row, 0, item)
            self.table.setItem(row, 1, QTableWidgetItem('Ready'))
            self.paths.append(path)
            if self.table.currentRow() < 0:
                self.table.selectRow(row)
        for error in result.errors:
            self.log.appendPlainText(error)

    def release_worker(self):
        self.worker.deleteLater()
        self.worker = None
        self.set_busy(False)

    def finish_scan(self):
        self.release_worker()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.status.setText(f'{len(self.paths)} images found · {self.skipped} skipped · {self.scan_errors} scan errors')

    def clear_all(self):
        if self.busy:
            return
        self.paths.clear()
        self.skipped = self.scan_errors = 0
        self.table.setRowCount(0)
        self.preview.canvas.clear_preview()
        self.preview.source_size = None
        self.preview.pixmap = None
        self.preview.details.setText('Source: —\nCrop: —\nOutput: —')
        self.log.clear()
        self.progress.setValue(0)
        self.status.setText('Ready')
        self.process.setEnabled(False)

    def start_processing(self):
        if self.busy or not self.paths:
            return
        self.processed = self.errors = 0
        self.set_busy(True)
        self.progress.setRange(0, len(self.paths))
        self.progress.setValue(0)
        for row in range(len(self.paths)):
            self.table.item(row, 1).setText('Queued')
        options = self.current_options()
        self.log.appendPlainText(self.summary.text())
        self.worker = Worker(list(self.paths), parent=self, options=options)
        self.worker.progress.connect(self.on_progress)
        self.worker.result.connect(self.on_result)
        self.worker.finished.connect(self.finish_processing)
        self.worker.start()

    def on_progress(self, current, total):
        self.status.setText(f'Processing {current} / {total}')

    def on_result(self, row, result):
        item = self.table.item(row, 1)
        if result.error:
            self.errors += 1
            item.setText('Error')
            item.setForeground(QColor('#fca5a5'))
            item.setToolTip(result.error)
            self.log.appendPlainText(f'ERROR — {result.source}\n{result.error}')
        else:
            self.processed += 1
            w, h = result.size
            details = []
            if result.original_size == result.cropped_size:
                details.append('no crop')
            if result.cropped_size != result.size:
                details.append('resized')
            if result.upscaling_blocked:
                details.append('upscaling avoided')
            suffix = ' · ' + ', '.join(details) if details else ''
            item.setText(f'{w} × {h}{suffix}')
            item.setForeground(QColor('#86efac'))
            item.setToolTip(str(result.output))
            self.log.appendPlainText(f'{result.output}\n{result.original_size} → crop {result.cropped_size}'
                                     f' → {result.size}{suffix}')
        self.progress.setValue(row + 1)

    def finish_processing(self):
        self.release_worker()
        self.status.setText(f'Finished: {self.processed} images processed, {self.skipped} skipped, '
                            f'{self.errors} errors · {self.scan_errors} scan errors')

    def closeEvent(self, event):
        if self.busy:
            self.status.setText('Please wait for the current operation to finish before closing.')
            event.ignore()
        else:
            event.accept()


def run():
    app = QApplication.instance() or QApplication([])
    app.setApplicationName('PhotoCropV2')
    app.setApplicationDisplayName('PhotoCropV2')
    app.setApplicationVersion(__version__)
    app.setOrganizationName('PhotoCrop')
    icon_path = resource_path('assets/photocrop.ico')
    if icon_path.is_file():
        app.setWindowIcon(QIcon(str(icon_path)))
    app.setStyle('Fusion')
    window = MainWindow()
    window.show()
    return app.exec()
