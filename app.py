from __future__ import annotations

import os
import sys
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import pymysql
from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Qt, Signal, Slot
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QStyle,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

APP_NAME = "MariaDB Step Migrator"
APP_VERSION = "1.3.0"
APP_AUTHOR = "jcbmca"


def build_app_styles(theme: str) -> str:
    if theme == "Oscuro":
        colors = {
            "window": "#15181c",
            "panel": "#1f242a",
            "panel_alt": "#252b33",
            "text": "#eef2f6",
            "muted": "#aab4c0",
            "border": "#3b4652",
            "field": "#111418",
            "field_focus": "#18212a",
            "primary": "#2f80ed",
            "primary_hover": "#4f9bff",
            "danger": "#d94f4f",
            "danger_hover": "#ef6b6b",
            "selection": "#315f92",
            "disabled": "#68717d",
        }
    else:
        colors = {
            "window": "#f5f7fa",
            "panel": "#ffffff",
            "panel_alt": "#eef2f6",
            "text": "#18202a",
            "muted": "#5f6b78",
            "border": "#cfd8e3",
            "field": "#ffffff",
            "field_focus": "#f8fbff",
            "primary": "#1f6fd1",
            "primary_hover": "#155ab2",
            "danger": "#c73e3e",
            "danger_hover": "#a93131",
            "selection": "#d7e8ff",
            "disabled": "#8b97a5",
        }

    return f"""
    QMainWindow, QWidget {{
        background: {colors["window"]};
        color: {colors["text"]};
        font-size: 13px;
    }}
    QGroupBox {{
        background: {colors["panel"]};
        border: 1px solid {colors["border"]};
        border-radius: 8px;
        margin-top: 10px;
        padding: 9px;
        font-weight: 600;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
        color: {colors["muted"]};
    }}
    QLabel {{
        color: {colors["text"]};
    }}
    QLineEdit, QSpinBox, QComboBox, QTextEdit, QListWidget {{
        background: {colors["field"]};
        color: {colors["text"]};
        border: 1px solid {colors["border"]};
        border-radius: 6px;
        padding: 6px 8px;
        selection-background-color: {colors["selection"]};
    }}
    QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QTextEdit:focus, QListWidget:focus {{
        background: {colors["field_focus"]};
        border-color: {colors["primary"]};
    }}
    QComboBox::drop-down {{
        border: 0;
        width: 28px;
    }}
    QListWidget::item {{
        border-radius: 4px;
        padding: 5px;
    }}
    QListWidget::item:selected {{
        background: {colors["selection"]};
        color: {colors["text"]};
    }}
    QPushButton {{
        background: {colors["panel_alt"]};
        color: {colors["text"]};
        border: 1px solid {colors["border"]};
        border-radius: 6px;
        padding: 7px 11px;
        font-weight: 600;
    }}
    QPushButton:hover {{
        border-color: {colors["primary"]};
    }}
    QPushButton:pressed {{
        background: {colors["field_focus"]};
    }}
    QPushButton:disabled {{
        color: {colors["disabled"]};
        background: {colors["panel"]};
    }}
    QPushButton#primaryButton {{
        background: {colors["primary"]};
        border-color: {colors["primary"]};
        color: white;
    }}
    QPushButton#primaryButton:hover {{
        background: {colors["primary_hover"]};
    }}
    QPushButton#dangerButton {{
        background: {colors["danger"]};
        border-color: {colors["danger"]};
        color: white;
    }}
    QPushButton#dangerButton:hover {{
        background: {colors["danger_hover"]};
    }}
    QToolButton {{
        background: {colors["panel_alt"]};
        color: {colors["text"]};
        border: 1px solid {colors["border"]};
        border-radius: 6px;
        padding: 7px 10px;
        font-weight: 600;
    }}
    QToolButton:hover {{
        border-color: {colors["primary"]};
    }}
    QToolButton:checked {{
        background: {colors["primary"]};
        border-color: {colors["primary"]};
        color: white;
    }}
    QSplitter::handle {{
        background: {colors["border"]};
    }}
    QProgressBar {{
        background: {colors["panel_alt"]};
        border: 1px solid {colors["border"]};
        border-radius: 5px;
        min-height: 8px;
        max-height: 8px;
    }}
    QProgressBar::chunk {{
        background: {colors["primary"]};
        border-radius: 5px;
    }}
    QStatusBar {{
        background: {colors["panel"]};
        color: {colors["muted"]};
        border-top: 1px solid {colors["border"]};
    }}
    """


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def quote_identifier(identifier: str) -> str:
    if not identifier:
        raise ValueError("El identificador no puede estar vacio.")
    return f"`{identifier.replace('`', '``')}`"


@dataclass(frozen=True)
class DbConfig:
    host: str
    port: int
    user: str
    password: str


class DatabaseClient:
    def __init__(self, config: DbConfig):
        self.config = config

    def connect(
        self,
        database: str | None = None,
        read_timeout: int | None = None,
        write_timeout: int | None = None,
    ) -> pymysql.connections.Connection:
        params: dict[str, Any] = dict(
            host=self.config.host,
            port=self.config.port,
            user=self.config.user,
            password=self.config.password,
            database=database,
            charset="utf8mb4",
            autocommit=True,
            connect_timeout=10,
            cursorclass=pymysql.cursors.Cursor,
        )
        if read_timeout is not None:
            params["read_timeout"] = read_timeout
        if write_timeout is not None:
            params["write_timeout"] = write_timeout
        return pymysql.connect(**params)

    def list_databases(self) -> list[str]:
        with self.connect(read_timeout=30, write_timeout=30) as conn:
            with conn.cursor() as cur:
                cur.execute("SHOW DATABASES")
                return [row[0] for row in cur.fetchall()]

    def list_tables(self, database: str) -> list[str]:
        sql = f"SHOW FULL TABLES FROM {quote_identifier(database)} WHERE Table_type = 'BASE TABLE'"
        with self.connect(read_timeout=30, write_timeout=30) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                return sorted(row[0] for row in cur.fetchall())

    def migrate_tables(
        self,
        source_db: str,
        target_db: str,
        tables: list[str],
        progress: Callable[[str], None],
    ) -> None:
        source = quote_identifier(source_db)
        target = quote_identifier(target_db)

        with self.connect() as conn:
            with conn.cursor() as cur:
                total = len(tables)
                for index, table in enumerate(tables, start=1):
                    table_name = quote_identifier(table)
                    sql = (
                        f"CREATE OR REPLACE TABLE {target}.{table_name} "
                        f"AS SELECT * FROM {source}.{table_name}"
                    )
                    progress(f"[{index}/{total}] Migrando {source_db}.{table} -> {target_db}.{table}")
                    cur.execute(sql)
                    progress(f"OK: {target_db}.{table}")

    def drop_tables(
        self,
        target_db: str,
        tables: list[str],
        progress: Callable[[str], None],
    ) -> None:
        target = quote_identifier(target_db)

        with self.connect(read_timeout=60, write_timeout=60) as conn:
            with conn.cursor() as cur:
                for table in tables:
                    table_name = quote_identifier(table)
                    progress(f"Borrando {target_db}.{table}")
                    cur.execute(f"DROP TABLE IF EXISTS {target}.{table_name}")
                    progress(f"OK: tabla borrada {target_db}.{table}")


class WorkerSignals(QObject):
    result = Signal(object)
    error = Signal(str)
    progress = Signal(str)
    finished = Signal()


class Worker(QRunnable):
    def __init__(self, fn: Callable[..., Any], *args: Any, **kwargs: Any):
        super().__init__()
        self.setAutoDelete(False)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            result = self.fn(*self.args, progress=self.signals.progress.emit, **self.kwargs)
            self.signals.result.emit(result)
        except Exception:
            self.signals.error.emit(traceback.format_exc())
        finally:
            self.signals.finished.emit()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.resize(1180, 760)

        self.client: DatabaseClient | None = None
        self.pool = QThreadPool.globalInstance()
        self.active_workers: list[Worker] = []
        self.task_sequence = 0
        self.busy_tasks = 0
        self.busy_message = ""
        self.busy_started_at = 0.0
        self.loaded_project: tuple[str, str] | None = None

        self.host_input = QLineEdit(os.getenv("MARIADB_SERVER", "127.0.0.1"))
        self.host_input.setPlaceholderText("127.0.0.1")
        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(int(os.getenv("MARIADB_PORT", "3306")))
        self.port_input.setFixedWidth(92)
        self.user_input = QLineEdit(os.getenv("MARIADB_USER", ""))
        self.user_input.setPlaceholderText("usuario")
        self.password_input = QLineEdit(os.getenv("MARIADB_PASS", ""))
        self.password_input.setPlaceholderText("clave")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.connect_button = QPushButton("Conectar")
        self.connect_button.setObjectName("primaryButton")
        self.refresh_button = QPushButton("Actualizar")
        self.refresh_button.setEnabled(False)
        self.load_project_button = QPushButton("Cargar tablas")
        self.load_project_button.setObjectName("primaryButton")
        self.theme_button = QToolButton()
        self.theme_button.setCheckable(True)
        self.theme_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.theme_button.setChecked(os.getenv("APP_THEME", "Claro") == "Oscuro")

        self.source_db_combo = QComboBox()
        self.target_db_combo = QComboBox()
        self.source_tables = QListWidget()
        self.source_tables.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.migration_tables = QListWidget()
        self.migration_tables.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.target_tables = QListWidget()
        self.target_tables.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)

        self.add_button = QPushButton("Agregar >")
        self.remove_button = QPushButton("< Quitar")
        self.up_button = QPushButton("Subir")
        self.down_button = QPushButton("Bajar")
        self.migrate_button = QPushButton("Migrar seleccion")
        self.migrate_button.setObjectName("primaryButton")
        self.delete_button = QPushButton("Borrar tablas destino")
        self.delete_button.setObjectName("dangerButton")
        self.reload_tables_button = QPushButton("Recargar tablas")
        self.busy_label = QLabel("Listo")
        self.version_label = QLabel(f"v{APP_VERSION} - {APP_AUTHOR}")
        self.busy_progress = QProgressBar()
        self.busy_progress.setRange(0, 0)
        self.busy_progress.setTextVisible(False)
        self.busy_progress.setVisible(False)
        self.busy_timer = QTimer(self)
        self.busy_timer.setInterval(500)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(120)

        self._build_ui()
        self._set_button_icons()
        self._connect_signals()
        self._set_database_controls_enabled(False)
        self.apply_theme(self.current_theme())
        self.statusBar().showMessage("Sin conexion")

    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(10, 8, 10, 8)
        root.setSpacing(8)

        top_group = QGroupBox("Conexion y proyecto")
        form = QGridLayout(top_group)
        form.setContentsMargins(10, 8, 10, 10)
        form.setHorizontalSpacing(8)
        form.setVerticalSpacing(6)
        form.addWidget(QLabel("Host"), 0, 0)
        form.addWidget(self.host_input, 0, 1)
        form.addWidget(QLabel("Puerto"), 0, 2)
        form.addWidget(self.port_input, 0, 3)
        form.addWidget(QLabel("Usuario"), 0, 4)
        form.addWidget(self.user_input, 0, 5)
        form.addWidget(QLabel("Clave"), 0, 6)
        form.addWidget(self.password_input, 0, 7)
        form.addWidget(self.theme_button, 0, 8)
        form.addWidget(self.connect_button, 0, 9)
        form.addWidget(self.refresh_button, 0, 10)
        form.addWidget(QLabel("Origen"), 1, 0)
        form.addWidget(self.source_db_combo, 1, 1, 1, 3)
        form.addWidget(QLabel("Destino"), 1, 4)
        form.addWidget(self.target_db_combo, 1, 5, 1, 3)
        form.addWidget(self.load_project_button, 1, 8, 1, 3)
        form.setColumnStretch(1, 2)
        form.setColumnStretch(5, 2)
        form.setColumnStretch(7, 2)
        root.addWidget(top_group)

        splitter = QSplitter()
        splitter.addWidget(self._source_panel())
        splitter.addWidget(self._migration_panel())
        splitter.addWidget(self._target_panel())
        splitter.setSizes([360, 360, 360])
        root.addWidget(splitter, 1)

        log_group = QGroupBox("Registro")
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(10, 8, 10, 10)
        log_layout.addWidget(self.log_output)
        root.addWidget(log_group)

        self.setCentralWidget(central)
        self.setStatusBar(QStatusBar())
        self.statusBar().addPermanentWidget(self.version_label)
        self.statusBar().addPermanentWidget(self.busy_label)
        self.statusBar().addPermanentWidget(self.busy_progress, 1)

    def _source_panel(self) -> QWidget:
        panel = QGroupBox("Tablas origen")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 8, 10, 10)
        layout.setSpacing(8)
        layout.addWidget(self.source_tables)
        layout.addWidget(self.add_button)
        return panel

    def _migration_panel(self) -> QWidget:
        panel = QGroupBox("Orden de migracion")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 8, 10, 10)
        layout.setSpacing(8)
        layout.addWidget(self.migration_tables)

        buttons = QHBoxLayout()
        buttons.addWidget(self.remove_button)
        buttons.addWidget(self.up_button)
        buttons.addWidget(self.down_button)
        layout.addLayout(buttons)
        layout.addWidget(self.migrate_button)
        return panel

    def _target_panel(self) -> QWidget:
        panel = QGroupBox("Tablas destino")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 8, 10, 10)
        layout.setSpacing(8)
        layout.addWidget(self.target_tables)
        layout.addWidget(self.reload_tables_button)
        layout.addWidget(self.delete_button)
        return panel

    def _connect_signals(self) -> None:
        self.connect_button.clicked.connect(self.connect_to_database)
        self.refresh_button.clicked.connect(self.load_databases)
        self.load_project_button.clicked.connect(self.load_selected_project_tables)
        self.add_button.clicked.connect(self.add_selected_tables)
        self.remove_button.clicked.connect(self.remove_selected_migration_tables)
        self.up_button.clicked.connect(lambda: self.move_migration_selection(-1))
        self.down_button.clicked.connect(lambda: self.move_migration_selection(1))
        self.migrate_button.clicked.connect(self.confirm_and_migrate)
        self.delete_button.clicked.connect(self.confirm_and_delete_target_tables)
        self.reload_tables_button.clicked.connect(self.reload_current_tables)
        self.theme_button.toggled.connect(self.toggle_theme)
        self.busy_timer.timeout.connect(self.update_busy_indicator)

    def _set_button_icons(self) -> None:
        style = self.style()
        icon_size = self.connect_button.iconSize()
        for button in (
            self.connect_button,
            self.refresh_button,
            self.load_project_button,
            self.add_button,
            self.remove_button,
            self.up_button,
            self.down_button,
            self.migrate_button,
            self.delete_button,
            self.reload_tables_button,
        ):
            button.setIconSize(icon_size)

        self.connect_button.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
        self.refresh_button.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.load_project_button.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
        self.add_button.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_ArrowRight))
        self.remove_button.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_ArrowLeft))
        self.up_button.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_ArrowUp))
        self.down_button.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_ArrowDown))
        self.migrate_button.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_ArrowForward))
        self.delete_button.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
        self.reload_tables_button.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.update_theme_button()

    def current_theme(self) -> str:
        return "Oscuro" if self.theme_button.isChecked() else "Claro"

    def toggle_theme(self, _checked: bool) -> None:
        self.apply_theme(self.current_theme())

    def apply_theme(self, theme: str) -> None:
        QApplication.instance().setStyleSheet(build_app_styles(theme))
        self.update_theme_button()

    def update_theme_button(self) -> None:
        style = self.style()
        if self.theme_button.isChecked():
            self.theme_button.setText("Oscuro")
            self.theme_button.setToolTip("Cambiar a tema claro")
            self.theme_button.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DialogNoButton))
        else:
            self.theme_button.setText("Claro")
            self.theme_button.setToolTip("Cambiar a tema oscuro")
            self.theme_button.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DialogYesButton))

    def _set_database_controls_enabled(self, enabled: bool) -> None:
        for widget in (
            self.source_db_combo,
            self.target_db_combo,
            self.load_project_button,
            self.source_tables,
            self.migration_tables,
            self.target_tables,
            self.add_button,
            self.remove_button,
            self.up_button,
            self.down_button,
            self.migrate_button,
            self.delete_button,
            self.reload_tables_button,
        ):
            widget.setEnabled(enabled)

    def _set_busy(self, busy: bool, message: str = "") -> None:
        if busy:
            if self.busy_tasks == 0:
                self.busy_started_at = time.monotonic()
                self.busy_timer.start()
                self.busy_progress.setVisible(True)
            self.busy_tasks += 1
            self.busy_message = message or self.busy_message
        else:
            self.busy_tasks = max(0, self.busy_tasks - 1)

        is_busy = self.busy_tasks > 0
        self.connect_button.setEnabled(not is_busy)
        self.refresh_button.setEnabled(not is_busy and self.client is not None)
        self._set_database_controls_enabled(not is_busy and self.client is not None)
        if not is_busy:
            self.busy_timer.stop()
            self.busy_progress.setVisible(False)
            self.busy_label.setText("Listo")
            self.busy_message = ""
        self.update_busy_indicator(message if busy else "")

    def update_busy_indicator(self, message: str = "") -> None:
        if self.busy_tasks <= 0:
            if message:
                self.statusBar().showMessage(message)
            return

        if message:
            self.busy_message = message
        elapsed = int(time.monotonic() - self.busy_started_at)
        text = f"{self.busy_message} ({self.busy_tasks} tarea/s, {elapsed}s)"
        self.busy_label.setText(text)
        self.statusBar().showMessage(text)

    def log(self, message: str) -> None:
        self.log_output.append(message)

    def config_from_form(self) -> DbConfig:
        return DbConfig(
            host=self.host_input.text().strip(),
            port=self.port_input.value(),
            user=self.user_input.text().strip(),
            password=self.password_input.text(),
        )

    def run_task(
        self,
        fn: Callable[..., Any],
        on_result: Callable[[Any], None] | None = None,
        busy_message: str = "Trabajando...",
        **kwargs: Any,
    ) -> None:
        self.task_sequence += 1
        task_name = f"Tarea {self.task_sequence}: {busy_message}"
        self.log(f"{task_name} iniciada")
        self._set_busy(True, busy_message)
        worker = Worker(fn, **kwargs)
        self.active_workers.append(worker)
        worker.signals.progress.connect(self.log)
        worker.signals.error.connect(self.show_task_error)
        if on_result is not None:
            worker.signals.result.connect(on_result)
        worker.signals.finished.connect(lambda w=worker, name=task_name: self.finish_task(w, name))
        self.pool.start(worker)

    def finish_task(self, worker: Worker, task_name: str) -> None:
        if worker in self.active_workers:
            self.active_workers.remove(worker)
        self.log(f"{task_name} finalizada")
        self._set_busy(False, "Listo")

    def show_task_error(self, details: str) -> None:
        self.log("ERROR:\n" + details)
        QMessageBox.critical(self, "Error", details.splitlines()[-1] if details else "Error desconocido")

    def connect_to_database(self) -> None:
        config = self.config_from_form()
        if not config.host or not config.user:
            QMessageBox.warning(self, "Datos incompletos", "Ingresa host y usuario.")
            return

        self.client = DatabaseClient(config)
        self.loaded_project = None
        self.source_tables.clear()
        self.target_tables.clear()
        self.migration_tables.clear()
        self.load_databases()

    def load_databases(self) -> None:
        if self.client is None:
            return

        def task(progress: Callable[[str], None]) -> list[str]:
            progress("Consultando bases disponibles...")
            return self.client.list_databases()

        self.run_task(task, self.populate_databases, "Conectando...")

    def populate_databases(self, databases: list[str]) -> None:
        current_source = self.source_db_combo.currentText() or os.getenv("MARIADB_NAME", "")
        current_target = self.target_db_combo.currentText()

        self.source_db_combo.blockSignals(True)
        self.target_db_combo.blockSignals(True)
        self.source_db_combo.clear()
        self.target_db_combo.clear()
        self.source_db_combo.addItems(databases)
        self.target_db_combo.addItems(databases)
        self._select_combo_text(self.source_db_combo, current_source)
        self._select_combo_text(self.target_db_combo, current_target)
        self.source_db_combo.blockSignals(False)
        self.target_db_combo.blockSignals(False)

        self.refresh_button.setEnabled(True)
        self._set_database_controls_enabled(True)
        self.log(f"Conexion OK. Bases visibles: {len(databases)}")
        if self.loaded_project is None and self.source_db_combo.currentText() and self.target_db_combo.currentText():
            self.log("Selecciona DB origen/destino y usa 'Cargar tablas' para iniciar el proyecto.")

    def _select_combo_text(self, combo: QComboBox, text: str) -> None:
        if not text:
            return
        index = combo.findText(text)
        if index >= 0:
            combo.setCurrentIndex(index)

    def reload_current_tables(self) -> None:
        self.load_selected_project_tables(force_reload=True)

    def load_selected_project_tables(self, force_reload: bool = False) -> None:
        source_db = self.source_db_combo.currentText()
        target_db = self.target_db_combo.currentText()
        if not source_db or not target_db:
            QMessageBox.warning(self, "DB incompleta", "Selecciona DB origen y DB destino.")
            return

        selected_project = (source_db, target_db)
        if self.loaded_project is not None and selected_project != self.loaded_project and not force_reload:
            old_source, old_target = self.loaded_project
            response = QMessageBox.question(
                self,
                "Cambiar proyecto",
                (
                    f"Proyecto actual: {old_source} -> {old_target}\n"
                    f"Nuevo proyecto: {source_db} -> {target_db}\n\n"
                    "Esto limpia la lista de migracion actual. Cambiar proyecto?"
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if response != QMessageBox.StandardButton.Yes:
                self._restore_loaded_project_selection()
                return

        if selected_project != self.loaded_project:
            self.source_tables.clear()
            self.target_tables.clear()
            self.migration_tables.clear()
            self.loaded_project = selected_project
            self.log(f"Proyecto cargado: {source_db} -> {target_db}")

        self.load_source_tables()
        self.load_target_tables()

    def _restore_loaded_project_selection(self) -> None:
        if self.loaded_project is None:
            return
        source_db, target_db = self.loaded_project
        self.source_db_combo.blockSignals(True)
        self.target_db_combo.blockSignals(True)
        self._select_combo_text(self.source_db_combo, source_db)
        self._select_combo_text(self.target_db_combo, target_db)
        self.source_db_combo.blockSignals(False)
        self.target_db_combo.blockSignals(False)

    def load_source_tables(self) -> None:
        self.load_tables(self.source_db_combo.currentText(), self.source_tables, clear_migration=False)

    def load_target_tables(self) -> None:
        self.load_tables(self.target_db_combo.currentText(), self.target_tables, clear_migration=False)

    def load_tables(self, database: str, list_widget: QListWidget, clear_migration: bool) -> None:
        if self.client is None or not database:
            return

        def task(progress: Callable[[str], None]) -> list[str]:
            progress(f"Consultando tablas de {database}...")
            return self.client.list_tables(database)

        def populate(tables: list[str]) -> None:
            list_widget.clear()
            list_widget.addItems(tables)
            if clear_migration:
                self.migration_tables.clear()
            self.log(f"{database}: {len(tables)} tablas")

        self.run_task(task, populate, f"Cargando tablas de {database}...")

    def add_selected_tables(self) -> None:
        existing = {self.migration_tables.item(i).text() for i in range(self.migration_tables.count())}
        for item in self.source_tables.selectedItems():
            if item.text() not in existing:
                self.migration_tables.addItem(item.text())
                existing.add(item.text())

    def remove_selected_migration_tables(self) -> None:
        for item in self.migration_tables.selectedItems():
            row = self.migration_tables.row(item)
            self.migration_tables.takeItem(row)

    def move_migration_selection(self, offset: int) -> None:
        selected_rows = sorted(
            [self.migration_tables.row(item) for item in self.migration_tables.selectedItems()],
            reverse=offset > 0,
        )
        for row in selected_rows:
            new_row = row + offset
            if new_row < 0 or new_row >= self.migration_tables.count():
                continue
            item = self.migration_tables.takeItem(row)
            self.migration_tables.insertItem(new_row, item)
            item.setSelected(True)

    def migration_table_names(self) -> list[str]:
        return [self.migration_tables.item(i).text() for i in range(self.migration_tables.count())]

    def selected_target_table_names(self) -> list[str]:
        return [item.text() for item in self.target_tables.selectedItems()]

    def confirm_and_migrate(self) -> None:
        if self.client is None:
            return
        source_db = self.source_db_combo.currentText()
        target_db = self.target_db_combo.currentText()
        tables = self.migration_table_names()

        if not source_db or not target_db:
            QMessageBox.warning(self, "DB incompleta", "Selecciona DB origen y DB destino.")
            return
        if source_db == target_db:
            QMessageBox.warning(self, "DB invalida", "La DB de origen y destino deben ser distintas.")
            return
        if not tables:
            QMessageBox.warning(self, "Sin tablas", "Agrega una o mas tablas al orden de migracion.")
            return

        response = QMessageBox.question(
            self,
            "Confirmar migracion",
            f"Se crearan o reemplazaran {len(tables)} tablas en {target_db}. Continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if response != QMessageBox.StandardButton.Yes:
            return

        self.run_task(
            self.client.migrate_tables,
            lambda _result: self.load_target_tables(),
            "Migrando tablas...",
            source_db=source_db,
            target_db=target_db,
            tables=tables,
        )

    def confirm_and_delete_target_tables(self) -> None:
        if self.client is None:
            return
        target_db = self.target_db_combo.currentText()
        tables = self.selected_target_table_names()

        if not target_db:
            QMessageBox.warning(self, "DB incompleta", "Selecciona una DB de destino.")
            return
        if not tables:
            QMessageBox.warning(self, "Sin tablas", "Selecciona una o mas tablas destino.")
            return

        response = QMessageBox.warning(
            self,
            "Confirmar borrado",
            f"Se borraran {len(tables)} tablas de {target_db}. Esta accion no se puede deshacer. Continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if response != QMessageBox.StandardButton.Yes:
            return

        self.run_task(
            self.client.drop_tables,
            lambda _result: self.load_target_tables(),
            "Borrando tablas...",
            target_db=target_db,
            tables=tables,
        )


def main() -> int:
    load_dotenv(Path(".env"))
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName(APP_AUTHOR)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
