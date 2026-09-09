"""Qt interface; discovery and image work run outside the GUI thread."""
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QCursor
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QFileDialog, QFrame, QHBoxLayout, QLabel,
    QMainWindow, QMenu, QPlainTextEdit, QProgressBar, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QHeaderView,
)

from .discovery import discover
from .processing import process_image


class Worker(QThread):
    discovered = Signal(object)
    progress = Signal(int, int)
    result = Signal(int, object)

    def __init__(self, paths, recursive=None, existing=(), parent=None):
        super().__init__(parent)
        self.paths, self.recursive, self.existing = paths, recursive, existing

    def run(self):
        if self.recursive is not None:
            self.discovered.emit(discover(self.paths, self.recursive, self.existing))
        else:
            for index, path in enumerate(self.paths):
                self.progress.emit(index + 1, len(self.paths))
                self.result.emit(index, process_image(path))


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
        self.setMinimumHeight(180)
        layout = QVBoxLayout(self)
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
            event.acceptProposedAction()

    def dropEvent(self, event):
        self.paths_added.emit([url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()])
        event.acceptProposedAction()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.clicked.emit()
        else:
            super().keyPressEvent(event)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.paths = []
        self.worker = None
        self.busy = False
        self.skipped = self.processed = self.errors = 0
        self.scan_errors = 0
        self.setWindowTitle('4:3 Photo Crop')
        self.resize(920, 760)
        self.setMinimumSize(660, 620)
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(30, 24, 30, 24)
        layout.setSpacing(14)
        title = QLabel('4:3 Photo Crop')
        title.setObjectName('title')
        layout.addWidget(title)
        subtitle = QLabel('Centered crop · Automatic orientation · Maximum JPEG quality')
        subtitle.setObjectName('muted')
        layout.addWidget(subtitle)
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
        layout.addWidget(self.table, 1)
        actions = QHBoxLayout()
        self.clear = QPushButton('Clear')
        self.clear.clicked.connect(self.clear_all)
        self.process = QPushButton('Process')
        self.process.setObjectName('primary')
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
            QWidget { background: #111827; color: #e5e7eb; font-family: "Segoe UI"; font-size: 13px; }
            QLabel#title { font-size: 28px; font-weight: 700; }
            QLabel#muted { color: #9ca3af; }
            QFrame#dropArea { background: #172438; border: 2px dashed #507099; border-radius: 14px; }
            QFrame#dropArea:hover, QFrame#dropArea:focus { border-color: #60a5fa; }
            QFrame#dropArea QLabel { background: transparent; border: none; }
            QLabel#dropTitle { font-size: 21px; font-weight: 600; }
            QPushButton { background: #263449; border: 1px solid #40516a; border-radius: 7px; padding: 10px 25px; }
            QPushButton:hover { background: #334660; }
            QPushButton#primary { background: #2563eb; border-color: #3b82f6; font-weight: 600; }
            QPushButton#primary:hover { background: #3478f6; }
            QPushButton:disabled { background: #202b3c; color: #64748b; border-color: #29364b; }
            QTableWidget, QPlainTextEdit { background: #172033; border: 1px solid #314057; border-radius: 6px; gridline-color: #29364b; }
            QHeaderView::section { background: #233047; border: none; padding: 8px; }
            QTableWidget::item { padding: 5px; }
            QProgressBar { border: none; border-radius: 5px; background: #263449; text-align: center; min-height: 18px; }
            QProgressBar::chunk { background: #2563eb; border-radius: 5px; }
            QMenu { background: #263449; padding: 6px; }
            QMenu::item { padding: 8px 24px; }
            QMenu::item:selected { background: #2563eb; }
        ''')

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
        for widget in (self.drop, self.recursive, self.clear):
            widget.setEnabled(not value)
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
        self.worker = Worker(list(self.paths), parent=self)
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
            unchanged = ' · no crop' if result.original_size == result.size else ''
            item.setText(f'{w} × {h}{unchanged}')
            item.setForeground(QColor('#86efac'))
            item.setToolTip(str(result.output))
            self.log.appendPlainText(str(result.output))
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
    app.setStyle('Fusion')
    window = MainWindow()
    window.show()
    return app.exec()
