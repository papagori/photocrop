"""Qt interface; discovery and image work run outside the GUI thread."""
import os
from pathlib import Path

from PIL import Image, ImageOps
from PIL.ImageQt import ImageQt
from PySide6.QtCore import QRectF, QSettings, Qt, QThread, QUrl, Signal
from PySide6.QtGui import QColor, QCursor, QDesktopServices, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QHBoxLayout, QLabel,
    QMainWindow, QMenu, QPlainTextEdit, QProgressBar, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget, QHeaderView, QStyle,
)

from .discovery import discover
from .classic_icons import classic_icon
from .export import FORMATS
from .geometry import crop_box, output_size
from .i18n import normalize_language, system_language, tr
from .processing import process_image
from .resources import resource_path
from .settings import ASPECT_RATIOS, ProcessingOptions, presets_for_ratio
from .themes import LinkLabel, ThemedComboBox, ToggleSwitch, normalize_theme, theme_stylesheet
from .version import __version__


GITHUB_URL = 'https://github.com/papagori/photocrop'


def open_output_folder(path):
    """Ask Windows to open one folder; failure must never affect the batch."""
    try:
        startfile = getattr(os, 'startfile')
        startfile(str(Path(path).resolve()))
        return True
    except (AttributeError, OSError):
        return False


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
            self.discovered.emit(discover(self.paths, self.recursive, self.existing,
                                          self.options.language))
        else:
            for index, path in enumerate(self.paths):
                self.progress.emit(index + 1, len(self.paths))
                self.result.emit(index, process_image(path, self.options))


class DropArea(QFrame):
    paths_added = Signal(list)
    clicked = Signal()

    def __init__(self, language='en'):
        super().__init__()
        self.language = language
        self.setObjectName('dropArea')
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFixedHeight(108)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon = QLabel()
        self.icon.setPixmap(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon).pixmap(28, 28))
        self.title = QLabel()
        self.title.setObjectName('dropTitle')
        self.hint = QLabel()
        self.hint.setObjectName('muted')
        for label in (self.icon, self.title, self.hint):
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            layout.addWidget(label)
        self.retranslate(language)

    def retranslate(self, language):
        self.language = language
        self.setAccessibleName(tr('drop_accessible', language))
        self.title.setText(tr('drop_title', language))
        self.hint.setText(tr('drop_hint', language))

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

    def __init__(self, language='en'):
        super().__init__()
        self.language = language
        self.pixmap = self.source_size = self.crop = None
        self.setMinimumSize(240, 100)
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
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, tr('preview_empty', self.language))
            return
        bounds = QRectF(self.rect().adjusted(10, 10, -10, -10))
        scaled = self.pixmap.size()
        scaled.scale(bounds.size().toSize(), Qt.AspectRatioMode.KeepAspectRatio)
        image_rect = QRectF(0, 0, scaled.width(), scaled.height())
        image_rect.moveCenter(bounds.center())
        painter.drawPixmap(image_rect.toRect(), self.pixmap)
        left, top, right, bottom = self.crop
        source_width, source_height = self.source_size
        scale_x, scale_y = image_rect.width() / source_width, image_rect.height() / source_height
        crop_rect = QRectF(image_rect.left() + left * scale_x, image_rect.top() + top * scale_y,
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
    def __init__(self, language='en'):
        super().__init__()
        self.source_size = self.pixmap = None
        self.setObjectName('previewPanel')
        self.setMinimumWidth(310)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)
        title_row = QHBoxLayout()
        title_row.setSpacing(7)
        self.icon = QLabel()
        self.icon.setPixmap(self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon).pixmap(18, 18))
        self.title = QLabel()
        self.title.setObjectName('sectionTitle')
        self.canvas = PreviewCanvas(language)
        self.details = QLabel()
        self.details.setObjectName('previewDetails')
        self.details.setFixedHeight(42)
        title_row.addWidget(self.icon)
        title_row.addWidget(self.title)
        title_row.addStretch()
        layout.addLayout(title_row)
        layout.addWidget(self.canvas, 1)
        layout.addWidget(self.details)
        self.retranslate(language)

    def retranslate(self, language):
        self.canvas.language = language
        self.canvas.update()
        self.title.setText(tr('preview', language))
        if self.source_size is None:
            self.details.setText(tr('preview_details_empty', language))


class MainWindow(QMainWindow):
    def __init__(self, language=None, settings=None, theme=None):
        super().__init__()
        self.app_settings = settings if settings is not None else QSettings('PhotoCrop', 'PhotoCropV2')
        stored = self.app_settings.value('language', '') if language is None else language
        self.language = normalize_language(stored or system_language())
        stored_theme = self.app_settings.value('theme', 'dark') if theme is None else theme
        self.theme = normalize_theme(stored_theme)
        self.paths, self.worker = [], None
        self.busy = False
        self.skipped = self.processed = self.errors = self.scan_errors = 0
        self.first_output_dir = None
        self.status_key, self.status_values = 'ready', {}
        icon_path = resource_path('assets/photocrop.ico')
        if icon_path.is_file():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.resize(1120, 850)
        self.setMinimumSize(920, 760)
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(26, 22, 26, 22)
        layout.setSpacing(9)

        header = QHBoxLayout()
        header.setSpacing(10)
        self.logo = QLabel()
        if icon_path.is_file():
            self.logo.setPixmap(QIcon(str(icon_path)).pixmap(34, 34))
        title = QLabel('PhotoCrop')
        title.setObjectName('title')
        version = QLabel(f'v{__version__}')
        version.setObjectName('versionBadge')
        self.language_label = QLabel()
        self.language_combo = ThemedComboBox()
        self.language_combo.addItem('English', 'en')
        self.language_combo.addItem('Français', 'fr')
        self.language_combo.addItem('日本語', 'ja')
        self.language_combo.setFixedWidth(150)
        self.language_combo.setCurrentIndex(self.language_combo.findData(self.language))
        self.theme_label = QLabel()
        self.theme_combo = ThemedComboBox()
        for theme_name in ('dark', 'light', 'classic'):
            self.theme_combo.addItem('', theme_name)
        self.theme_combo.setFixedWidth(170)
        self.theme_combo.setCurrentIndex(self.theme_combo.findData(self.theme))
        header.addWidget(self.logo)
        header.addWidget(title)
        header.addWidget(version)
        header.addStretch()
        header.addWidget(self.language_label)
        header.addWidget(self.language_combo)
        header.addWidget(self.theme_label)
        header.addWidget(self.theme_combo)
        layout.addLayout(header)

        self.subtitle = QLabel()
        self.subtitle.setObjectName('muted')
        layout.addWidget(self.subtitle)
        self.add_label = QLabel()
        self.add_label.setObjectName('stepLabel')
        layout.addWidget(self.add_label)
        self.drop = DropArea(self.language)
        self.drop.clicked.connect(self.choose_input)
        self.drop.paths_added.connect(self.add_paths)
        layout.addWidget(self.drop)
        self.recursive = ToggleSwitch()
        layout.addWidget(self.recursive)

        self.table = QTableWidget(0, 2)
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
        self.file_title = QLabel()
        self.file_title.setObjectName('sectionTitle')
        file_column.addWidget(self.file_title)
        file_column.addWidget(self.table, 1)
        content.addLayout(file_column, 3)
        self.preview = PreviewPanel(self.language)
        content.addWidget(self.preview, 2)

        settings_layout = QHBoxLayout()
        settings_layout.setContentsMargins(14, 12, 14, 12)
        settings_layout.setSpacing(14)
        aspect_column = QVBoxLayout()
        aspect_column.setSpacing(6)
        self.aspect_label = QLabel()
        self.aspect = ThemedComboBox()
        for label, ratio in ASPECT_RATIOS.items():
            self.aspect.addItem(label, ratio)
        self.aspect.setCurrentText('4:3')
        self.aspect_label.setBuddy(self.aspect)
        aspect_column.addWidget(self.aspect_label)
        aspect_column.addWidget(self.aspect)
        size_column = QVBoxLayout()
        size_column.setSpacing(6)
        self.size_label = QLabel()
        self.output_size = ThemedComboBox()
        self.output_size.setMaxVisibleItems(10)
        self.size_label.setBuddy(self.output_size)
        size_column.addWidget(self.size_label)
        size_column.addWidget(self.output_size)
        format_column = QVBoxLayout()
        format_column.setSpacing(6)
        self.format_label = QLabel()
        self.output_format = ThemedComboBox()
        format_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)
        for name in FORMATS:
            self.output_format.addItem(format_icon, name, name)
        self.format_label.setBuddy(self.output_format)
        format_column.addWidget(self.format_label)
        format_column.addWidget(self.output_format)
        settings_layout.addLayout(aspect_column, 2)
        settings_layout.addLayout(size_column, 3)
        settings_layout.addLayout(format_column, 2)
        option_column = QVBoxLayout()
        self.upscaling = ToggleSwitch()
        self.open_when_finished = ToggleSwitch()
        self.open_when_finished.setChecked(self.app_settings.value('open_output_folder', True, type=bool))
        option_column.addWidget(self.upscaling)
        option_column.addWidget(self.open_when_finished)
        settings_layout.addLayout(option_column, 3)
        settings_panel = QFrame()
        settings_panel.setObjectName('settingsPanel')
        settings_panel.setLayout(settings_layout)
        layout.addWidget(settings_panel)
        self.summary = QLabel()
        self.summary.setObjectName('muted')
        self.summary.setWordWrap(True)
        self.summary.setFixedHeight(24)
        layout.addWidget(self.summary)
        layout.addLayout(content, 1)

        actions = QHBoxLayout()
        self.clear = QPushButton()
        self.clear.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
        self.clear.setMinimumWidth(96)
        self.clear.clicked.connect(self.clear_all)
        self.process = QPushButton()
        self.process.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
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
        self.status = QLabel()
        self.status.setWordWrap(True)
        self.status.setFixedHeight(22)
        layout.addWidget(self.status)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setFixedHeight(78)
        layout.addWidget(self.log)

        self.footer = QFrame()
        self.footer.setObjectName('footer')
        self.footer.setFixedHeight(28)
        footer_layout = QHBoxLayout(self.footer)
        footer_layout.setContentsMargins(10, 2, 10, 2)
        self.footer_gpl = QLabel()
        self.footer_github = LinkLabel()
        self.footer_github.setObjectName('footerLink')
        self.footer_github.clicked.connect(self.open_github)
        footer_layout.addWidget(self.footer_gpl)
        footer_layout.addStretch()
        footer_layout.addWidget(self.footer_github)
        layout.addWidget(self.footer)

        self.output_size.currentIndexChanged.connect(self.output_changed)
        self.aspect.currentIndexChanged.connect(self.aspect_changed)
        self.upscaling.toggled.connect(self.settings_changed)
        self.output_format.currentIndexChanged.connect(self.settings_changed)
        self.language_combo.currentIndexChanged.connect(self.language_changed)
        self.theme_combo.currentIndexChanged.connect(self.theme_changed)
        self.open_when_finished.toggled.connect(
            lambda checked: self.app_settings.setValue('open_output_folder', checked))
        self.aspect_changed()
        self.retranslate_ui()
        self.apply_theme()

    def t(self, key, **values):
        return tr(key, self.language, **values)

    def preset_text(self, preset, portrait=False):
        if preset.key == 'maximum':
            return self.t('maximum')
        if preset.key == 'original':
            return self.t('original')
        if preset.long_edge:
            return self.t('long_edge', edge=preset.long_edge)
        width, height = preset.dimensions
        return self.t('portrait_size', height=height, width=width) if portrait else f'{width} × {height}'

    def language_changed(self):
        self.language = normalize_language(self.language_combo.currentData())
        self.app_settings.setValue('language', self.language)
        self.retranslate_ui()
        self.apply_theme()

    def theme_changed(self):
        self.theme = normalize_theme(self.theme_combo.currentData())
        self.app_settings.setValue('theme', self.theme)
        self.apply_theme()

    def apply_theme(self):
        self.setStyleSheet(theme_stylesheet(self.theme, self.language))
        for toggle in (self.recursive, self.upscaling, self.open_when_finished):
            toggle.set_theme(self.theme)
        for combo in (self.language_combo, self.theme_combo, self.aspect,
                      self.output_size, self.output_format):
            combo.set_theme(self.theme)
        self.apply_icons()

    def apply_icons(self):
        classic = self.theme == 'classic'
        self.icon_theme = 'classic' if classic else 'modern'

        def themed(name, standard):
            return classic_icon(name) if classic else self.style().standardIcon(standard)

        self.drop.icon.setPixmap(themed('folder', QStyle.StandardPixmap.SP_DirOpenIcon).pixmap(28, 28))
        self.preview.icon.setPixmap(themed('preview', QStyle.StandardPixmap.SP_FileIcon).pixmap(18, 18))
        self.clear.setIcon(themed('trash', QStyle.StandardPixmap.SP_TrashIcon))
        self.process.setIcon(themed('process', QStyle.StandardPixmap.SP_DialogApplyButton))
        combo_icons = (
            (self.language_combo, themed('language', QStyle.StandardPixmap.SP_FileDialogInfoView)),
            (self.theme_combo, themed('theme', QStyle.StandardPixmap.SP_DesktopIcon)),
            (self.aspect, themed('image', QStyle.StandardPixmap.SP_FileIcon)),
            (self.output_size, themed('monitor', QStyle.StandardPixmap.SP_ComputerIcon)),
            (self.output_format, themed('format', QStyle.StandardPixmap.SP_DriveHDIcon)),
        )
        for combo, icon in combo_icons:
            for index in range(combo.count()):
                combo.setItemIcon(index, icon)

    def open_github(self, _link=GITHUB_URL):
        return QDesktopServices.openUrl(QUrl(GITHUB_URL))

    def retranslate_ui(self):
        self.setWindowTitle(self.t('window_title', version=__version__))
        self.language_label.setText(self.t('language'))
        self.theme_label.setText(self.t('theme'))
        for index, key in enumerate(('theme_dark', 'theme_light', 'theme_classic')):
            self.theme_combo.setItemText(index, self.t(key))
        self.subtitle.setText(self.t('subtitle'))
        self.add_label.setText(self.t('add_images_step'))
        self.drop.retranslate(self.language)
        self.recursive.setText(self.t('include_subfolders'))
        self.recursive.setToolTip(self.t('include_subfolders_tip'))
        self.table.setHorizontalHeaderLabels([self.t('source_image'), self.t('result')])
        self.file_title.setText(self.t('selected_files'))
        self.preview.retranslate(self.language)
        self.aspect_label.setText(self.t('aspect_ratio'))
        self.aspect.setItemText(0, self.t('ratio_original'))
        self.aspect.setAccessibleName(self.t('aspect_accessible'))
        self.size_label.setText(self.t('output_size'))
        self.output_size.setAccessibleName(self.t('output_size_accessible'))
        self.format_label.setText(self.t('output_format'))
        self.output_format.setAccessibleName(self.t('output_format_accessible'))
        self.upscaling.setText(self.t('allow_upscaling'))
        self.upscaling.setToolTip(self.t('allow_upscaling_tip'))
        self.open_when_finished.setText(self.t('open_output'))
        self.open_when_finished.setToolTip(self.t('open_output_tip'))
        self.clear.setText(self.t('clear'))
        self.process.setText(self.t('process'))
        self.log.setPlaceholderText(self.t('log_placeholder'))
        self.footer_gpl.setText(self.t('footer_gpl'))
        self.footer_github.setText(self.t('footer_github'))
        self.set_status(self.status_key, **self.status_values)
        preset = self.output_size.currentData()
        self.populate_output_sizes(preset.key if preset else None)
        self.refresh_preview()

    def set_status(self, key, **values):
        self.status_key, self.status_values = key, values
        self.status.setText(self.t(key, **values))

    def current_options(self):
        return ProcessingOptions(self.aspect.currentData(), self.output_size.currentData(),
                                 self.upscaling.isChecked(), self.output_format.currentData(), self.language)

    def aspect_changed(self):
        current = self.output_size.currentData()
        preferred = current.key if current and current.key in ('maximum', 'original') else None
        self.populate_output_sizes(preferred)

    def populate_output_sizes(self, preferred_key=None):
        portrait = bool(self.preview.source_size and self.preview.source_size[1] > self.preview.source_size[0])
        self.output_size.blockSignals(True)
        self.output_size.clear()
        selected_index = 0
        ratio_key = list(ASPECT_RATIOS)[self.aspect.currentIndex()]
        for index, preset in enumerate(presets_for_ratio(ratio_key)):
            self.output_size.addItem(self.preset_text(preset, portrait), preset)
            if preset.key == preferred_key:
                selected_index = index
        self.output_size.setCurrentIndex(selected_index)
        size_icon = (classic_icon('monitor') if self.theme == 'classic'
                     else self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        for index in range(self.output_size.count()):
            self.output_size.setItemIcon(index, size_icon)
        self.output_size.blockSignals(False)
        self.output_changed()

    def output_changed(self):
        preset = self.output_size.currentData()
        if preset is None:
            return
        self.aspect.setEnabled(not self.busy)
        self.aspect.setToolTip(self.t('portrait_tip'))
        can_resize = preset.dimensions is not None or preset.long_edge is not None
        self.upscaling.setEnabled(not self.busy and can_resize)
        self.settings_changed()

    def settings_changed(self):
        preset = self.output_size.currentData()
        if preset is None:
            return
        portrait = bool(self.preview.source_size and self.preview.source_size[1] > self.preview.source_size[0])
        parts = [self.aspect.currentText(), self.preset_text(preset, portrait)]
        if preset.dimensions is not None or preset.long_edge is not None:
            parts.append(self.t('upscaling_allowed' if self.upscaling.isChecked() else 'no_upscaling'))
        parts.append(self.t(f'format_quality_{self.output_format.currentData()}'))
        self.refresh_preview()
        self.summary.setText(' • '.join(parts))

    def preview_selection_changed(self, current_row, _current_column, _previous_row, _previous_column):
        self.load_preview(current_row)

    def load_preview(self, row):
        if row < 0 or row >= len(self.paths):
            self.preview.canvas.clear_preview()
            self.preview.source_size = None
            self.preview.details.setText(self.t('preview_details_empty'))
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
            self.preview.source_size, self.preview.pixmap = source_size, pixmap
            if previous_portrait != (source_size[1] > source_size[0]):
                preset = self.output_size.currentData()
                self.populate_output_sizes(preset.key if preset else None)
            else:
                self.refresh_preview()
        except Exception as exc:
            self.preview.canvas.clear_preview()
            self.preview.source_size = None
            self.preview.details.setText(self.t('preview_unavailable', error=f'{type(exc).__name__}: {exc}'))

    def refresh_preview(self):
        source_size = self.preview.source_size
        if not source_size or self.output_size.currentData() is None:
            return
        box = crop_box(*source_size, self.aspect.currentData())
        cropped_size = box[2] - box[0], box[3] - box[1]
        final_size, blocked = output_size(cropped_size, self.current_options(),
                                          portrait=source_size[1] > source_size[0])
        self.preview.canvas.set_preview(self.preview.pixmap, source_size, box)
        suffix = f" ({self.t('upscaling_avoided')})" if blocked else ''
        self.preview.details.setText(
            f"{self.t('source')}: {source_size[0]} × {source_size[1]}\n"
            f"{self.t('crop')}: {cropped_size[0]} × {cropped_size[1]}\n"
            f"{self.t('output')}: {final_size[0]} × {final_size[1]}{suffix}")

    def choose_input(self):
        menu = QMenu(self)
        files = menu.addAction(self.t('add_files'))
        folder = menu.addAction(self.t('add_folder'))
        choice = menu.exec(QCursor.pos())
        if choice == files:
            paths, _ = QFileDialog.getOpenFileNames(
                self, self.t('add_images_dialog'), '', self.t('image_filter'))
            self.add_paths(paths)
        elif choice == folder:
            path = QFileDialog.getExistingDirectory(self, self.t('add_folder_dialog'))
            if path:
                self.add_paths([path])

    def set_busy(self, value):
        self.busy = value
        for widget in (self.drop, self.recursive, self.clear, self.output_size, self.output_format,
                       self.language_combo, self.theme_combo):
            widget.setEnabled(not value)
        self.output_changed()
        self.process.setEnabled(not value and bool(self.paths))

    def add_paths(self, paths):
        if self.busy or not paths:
            return
        self.set_busy(True)
        self.set_status('looking')
        self.progress.setRange(0, 0)
        scan_options = ProcessingOptions(language=self.language)
        self.worker = Worker(list(paths), self.recursive.isChecked(), tuple(self.paths), self,
                             options=scan_options)
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
            self.table.setItem(row, 1, QTableWidgetItem(self.t('item_ready')))
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
        self.set_status('scan_finished', count=len(self.paths), skipped=self.skipped, errors=self.scan_errors)

    def clear_all(self):
        if self.busy:
            return
        self.paths.clear()
        self.skipped = self.scan_errors = 0
        self.table.setRowCount(0)
        self.preview.canvas.clear_preview()
        self.preview.source_size = self.preview.pixmap = None
        self.preview.details.setText(self.t('preview_details_empty'))
        self.log.clear()
        self.progress.setValue(0)
        self.set_status('ready')
        self.process.setEnabled(False)

    def start_processing(self):
        if self.busy or not self.paths:
            return
        self.processed = self.errors = 0
        self.first_output_dir = None
        self.set_busy(True)
        self.progress.setRange(0, len(self.paths))
        self.progress.setValue(0)
        for row in range(len(self.paths)):
            self.table.item(row, 1).setText(self.t('queued'))
        self.log.appendPlainText(self.summary.text())
        self.worker = Worker(list(self.paths), parent=self, options=self.current_options())
        self.worker.progress.connect(self.on_progress)
        self.worker.result.connect(self.on_result)
        self.worker.finished.connect(self.finish_processing)
        self.worker.start()

    def on_progress(self, current, total):
        self.set_status('processing', current=current, total=total)

    def on_result(self, row, result):
        item = self.table.item(row, 1)
        if result.error:
            self.errors += 1
            item.setText(self.t('error'))
            item.setForeground(QColor('#fca5a5'))
            item.setToolTip(result.error)
            self.log.appendPlainText(self.t('error_log', source=result.source, error=result.error))
        else:
            self.processed += 1
            if self.first_output_dir is None:
                self.first_output_dir = result.output.parent
            details = []
            if result.original_size == result.cropped_size:
                details.append(self.t('no_crop'))
            if result.cropped_size != result.size:
                details.append(self.t('resized'))
            if result.upscaling_blocked:
                details.append(self.t('upscaling_avoided'))
            suffix = ' • ' + ', '.join(details) if details else ''
            item.setText(f'{result.size[0]} × {result.size[1]}{suffix}')
            item.setForeground(QColor('#86efac'))
            item.setToolTip(str(result.output))
            self.log.appendPlainText(str(result.output))
            self.log.appendPlainText(self.t('result_log', original=result.original_size,
                                            cropped=result.cropped_size, final=result.size, suffix=suffix))
        self.progress.setValue(row + 1)

    def finish_processing(self):
        self.release_worker()
        self.set_status('finished', processed=self.processed, skipped=self.skipped,
                        errors=self.errors, scan_errors=self.scan_errors)
        if (self.open_when_finished.isChecked() and self.processed and not self.errors
                and self.first_output_dir is not None):
            open_output_folder(self.first_output_dir)

    def closeEvent(self, event):
        if self.busy:
            self.set_status('wait_close')
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
