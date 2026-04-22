import os
import json
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTabWidget, QFileDialog, QDialog,
                             QLineEdit, QInputDialog, QFrame, QTableWidgetItem,
                             QMessageBox, QStyle, QCheckBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon, QPixmap, QPainter, QColor
from ui.common_widgets import ExcelTable, StepDialog
from services.file_service import FileService
from services.scrape_service import ScrapeService
from services.ui_service import UIService


def create_dashboard(parent, layout, t, log_func=None, clear_log_func=None, lang="zh"):
    # 获取 UI 设置
    font_settings = UIService.get_font_settings()

    # 字体设置
    base_font = QFont(font_settings.get("font_family"), font_settings.get("font_size"))
    btn_font = QFont(font_settings.get("font_family"), font_settings.get("btn_font_size"))

    # 记录日志
    def log(msg, color="black"):
        if log_func:
            log_func(msg, color)

    # 初始化抓取服务
    scrape_service = ScrapeService(log_func=log, t=t)

    # 注册清理函数，当标签页关闭时停止抓取
    def cleanup():
        scrape_service.stop_scrape()

    parent.cleanup = cleanup

    fields_path = os.path.join("config", "fields.json")
    fields_data = FileService.load_json(fields_path)
    fields_config = fields_data.get("fields", [])

    # 分隔线
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setFrameShadow(QFrame.Sunken)
    line.setStyleSheet("background-color: #e0e0e0; margin: 10px 0;")
    layout.addWidget(line)

    file_layout = QHBoxLayout()
    file_label = QLabel(f"{t('current_file')}: {t('no_file')}")
    file_label.setFont(base_font)
    btn_select_file = QPushButton(t("select_excel"))
    btn_select_file.setFont(btn_font)
    file_layout.addWidget(file_label)
    file_layout.addWidget(btn_select_file)
    file_layout.addStretch()
    layout.addLayout(file_layout)

    toolbar_layout = QHBoxLayout()
    btn_add_step = QPushButton(t("add_step"))
    btn_del_step = QPushButton(t("del_step"))
    btn_add_sheet = QPushButton(t("add_sheet"))
    btn_del_sheet = QPushButton(t("del_sheet"))
    btn_save = QPushButton(t("save_steps"))

    btn_start = QPushButton(t("start_scrape"))
    btn_stop = QPushButton(t("stop_scrape"))

    btn_style = UIService.get_style("button")

    # 红色和绿色文字样式的专门定义
    red_text_style = btn_style.replace("color: #1d1d1f;", "color: #ff3b30;")
    green_text_style = btn_style.replace("color: #1d1d1f;", "color: #34c759;")
    black_text_style = btn_style.replace("color: #1d1d1f;", "color: black;")

    for btn in [btn_add_step, btn_add_sheet, btn_save]:
        btn.setStyleSheet(btn_style)
        btn.setFont(btn_font)
        toolbar_layout.addWidget(btn)

    for btn in [btn_del_step, btn_del_sheet]:
        btn.setStyleSheet(red_text_style)
        btn.setFont(btn_font)
        toolbar_layout.addWidget(btn)

    # 禁止拖拽复选框
    cb_disable_drag = QCheckBox(t("disable_drag"))
    cb_disable_drag.setFont(base_font)
    cb_disable_drag.setChecked(True)
    toolbar_layout.addWidget(cb_disable_drag)

    toolbar_layout.addStretch()
    layout.addLayout(toolbar_layout)

    sheet_tabs = QTabWidget()
    sheet_tabs.setFont(base_font)
    sheet_tabs.setStyleSheet(UIService.get_style("sheet_tabs"))
    # 强制设置标签栏属性以支持左对齐和自适应宽度 (解决 Mac 下居中问题)
    sheet_tabs.tabBar().setExpanding(False)
    sheet_tabs.tabBar().setProperty("alignment", Qt.AlignLeft)
    sheet_tabs.setDocumentMode(False)
    layout.addWidget(sheet_tabs)

    # Scrape control bar (Moved to bottom)
    scrape_bar = QHBoxLayout()

    def get_colored_icon(standard_icon, color_str):
        pixmap = parent.style().standardIcon(standard_icon).pixmap(24, 24)
        painter = QPainter(pixmap)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), QColor(color_str))
        painter.end()
        return QIcon(pixmap)

    btn_start.setStyleSheet(black_text_style)
    btn_start.setFont(btn_font)
    btn_start.setIcon(get_colored_icon(QStyle.SP_MediaPlay, "#34c759"))
    scrape_bar.addWidget(btn_start)

    btn_stop.setStyleSheet(black_text_style)
    btn_stop.setFont(btn_font)
    btn_stop.setIcon(get_colored_icon(QStyle.SP_MediaStop, "#ff3b30"))
    scrape_bar.addWidget(btn_stop)

    btn_clear_cache = QPushButton(t("clear_chrome_cache"))
    btn_clear_cache.setStyleSheet(black_text_style)
    btn_clear_cache.setFont(btn_font)
    btn_clear_cache.setIcon(get_colored_icon(QStyle.SP_TrashIcon, "#007aff"))
    scrape_bar.addWidget(btn_clear_cache)

    btn_kill_processes = QPushButton(t("kill_chrome_processes"))
    btn_kill_processes.setStyleSheet(black_text_style)
    btn_kill_processes.setFont(btn_font)
    btn_kill_processes.setIcon(get_colored_icon(QStyle.SP_BrowserStop, "#ff9500"))
    scrape_bar.addWidget(btn_kill_processes)

    btn_clear_logs = QPushButton(t("clear_logs"))
    btn_clear_logs.setStyleSheet(black_text_style)
    btn_clear_logs.setFont(btn_font)
    btn_clear_logs.setIcon(get_colored_icon(QStyle.SP_DialogResetButton, "#5856d6"))
    scrape_bar.addWidget(btn_clear_logs)

    scrape_bar.addStretch()
    layout.addLayout(scrape_bar)

    def on_drag_lock_changed(state):
        enabled = (state == Qt.Unchecked)
        for i in range(sheet_tabs.count()):
            table = sheet_tabs.widget(i)
            if hasattr(table, "_set_drag_enabled"):
                table._set_drag_enabled(enabled)

    cb_disable_drag.stateChanged.connect(on_drag_lock_changed)

    current_file = [None]

    def load_initial_file():
        default_path = "scraping_config_example.xlsx"
        # 确保模板存在
        FileService.ensure_excel_template(default_path, fields_config, t)

        current_file[0] = default_path
        file_label.setText(f"{t('current_file')}: {os.path.basename(default_path)}")
        log(f"{t('loading_default_config')}: {default_path}")
        data = FileService.load_excel(default_path, fields_config)
        sheet_tabs.clear()
        if data:
            for name, rows in data.items(): add_sheet(name, rows, silent=True)
            log(f"{t('excel_loaded_success')}: {len(data)}")
        else:
            # 如果是新生成的空文件，至少加一个默认 Sheet
            add_sheet("ScrapingSteps", silent=True)
            log(f"{t('create_default_sheet')}: ScrapingSteps", "orange")

    def perform_auto_save():
        """ 内部自动保存函数，执行保存但不弹出提示框。 """
        if not current_file[0]:
            return
        data = {}
        for i in range(sheet_tabs.count()):
            name = sheet_tabs.tabText(i)
            table = sheet_tabs.widget(i)
            rows = []
            for r in range(table.rowCount()):
                row = [table.item(r, c).text() if table.item(r, c) else "" for c in range(table.columnCount())]
                rows.append(row)
            data[name] = rows
        FileService.save_excel(current_file[0], data, fields_config, t)

    def add_sheet(name=None, rows=None, silent=False):
        if name is None:
            name, ok = QInputDialog.getText(parent, t("new_sheet"), f"{t('input_sheet_name')}:", QLineEdit.Normal,
                                            f"Sheet{sheet_tabs.count() + 1}")
            if not (ok and name): return

        table = ExcelTable(fields_config, t, lang=lang)
        # 根据当前复选框状态设置拖拽
        if hasattr(table, "_set_drag_enabled"):
            table._set_drag_enabled(not cb_disable_drag.isChecked())

        table.setFont(base_font)
        if rows:
            for r_idx, row_data in enumerate(rows):
                table.insertRow(r_idx)
                for c_idx, val in enumerate(row_data):
                    table.setItem(r_idx, c_idx, QTableWidgetItem(str(val) if val is not None else ""))
            table.on_data_structure_changed()

        table.cellDoubleClicked.connect(lambda r, c: on_edit_step(table, r))
        sheet_tabs.addTab(table, name)
        sheet_tabs.setCurrentWidget(table)
        if not silent:
            perform_auto_save()

    def on_edit_step(table, row):
        """
        双击行时弹出编辑对话框。
        """
        try:
            row_data = [table.item(row, col).text() if table.item(row, col) else "" for col in
                        range(table.columnCount())]
            dialog = StepDialog(parent, fields_config, t, initial_data=row_data, lang=lang)
            dialog.setWindowTitle(t("step_detail"))
            if dialog.exec_() == QDialog.Accepted:
                new_data = dialog.get_data()
                for col, val in enumerate(new_data):
                    table.setItem(row, col, QTableWidgetItem(str(val)))
                table.on_data_structure_changed()
                perform_auto_save()
                log(f"{t('update_step_data_success')}: {t('id')} {row + 1}")
        except Exception as e:
            msg = f"{t('update_step_err')}: {str(e)}"
            log(msg, "red")
            QMessageBox.critical(parent, t("error") if "error" in t else "Error", msg)

    def on_select_file():
        """
        手动选择 Excel 文件。
        """
        try:
            path, _ = QFileDialog.getOpenFileName(parent, t("select_excel"), "", "Excel Files (*.xlsx *.xls)")
            if path:
                current_file[0] = path
                file_label.setText(f"{t('current_file')}: {os.path.basename(path)}")
                log(f"{t('switch_file')}: {path}", "green")
                data = FileService.load_excel(path, fields_config)
                sheet_tabs.clear()
                for name, rows in data.items(): add_sheet(name, rows, silent=True)
                log(t("load_file_success"))
        except Exception as e:
            msg = f"{t('open_file_err')}: {str(e)}"
            log(msg, "red")
            QMessageBox.critical(parent, t("error") if "error" in t else "Error", msg)

    def on_add_step():
        """
        按下 '添加步骤' 按钮时的处理逻辑。
        """
        try:
            table = sheet_tabs.currentWidget()
            if not table: return
            dialog = StepDialog(parent, fields_config, t, lang=lang)
            dialog.setWindowTitle(t("step_detail"))
            if dialog.exec_() == QDialog.Accepted:
                data = dialog.get_data()
                row = table.rowCount()
                table.insertRow(row)
                for col, val in enumerate(data): table.setItem(row, col, QTableWidgetItem(str(val)))
                table.on_data_structure_changed()
                perform_auto_save()
                log(f"{t('add_step_data_success')}: {data[1] if len(data) > 1 else t('unnamed')}")
        except Exception as e:
            msg = f"{t('add_step_err')}: {str(e)}"
            log(msg, "red")
            QMessageBox.critical(parent, t("error") if "error" in t else "Error", msg)

    def on_del_step():
        """
        删除选中的步骤。
        """
        try:
            table = sheet_tabs.currentWidget()
            if not table: return
            row = table.currentRow()
            if row != -1:
                table.removeRow(row)
                table.on_data_structure_changed()
                perform_auto_save()
                log(f"{t('del_step_success')}: {t('field_id')} {row + 1}", "orange")
        except Exception as e:
            msg = f"{t('del_step_failed')}: {str(e)}"
            log(msg, "red")
            QMessageBox.critical(parent, t("error") if "error" in t else "Error", msg)

    def on_del_sheet():
        """
        删除当前选中的 Sheet。
        """
        try:
            idx = sheet_tabs.currentIndex()
            if idx != -1:
                name = sheet_tabs.tabText(idx)
                sheet_tabs.removeTab(idx)
                perform_auto_save()
                log(f"{t('del_sheet_success')}: {name}", "orange")
        except Exception as e:
            msg = f"{t('del_sheet_failed')}: {str(e)}"
            log(msg, "red")
            QMessageBox.critical(parent, t("error") if "error" in t else "Error", msg)

    def on_save():
        if not current_file[0]:
            path, _ = QFileDialog.getSaveFileName(parent, t("save_steps"), "steps.xlsx", "Excel Files (*.xlsx)")
            if not path: return
            current_file[0] = path
            file_label.setText(f"{t('current_file')}: {os.path.basename(path)}")

        perform_auto_save()
        QMessageBox.information(parent, t("success"), t("save_success"))

    def on_start_scrape():
        """开始抓取当前选中的 Sheet 内容"""
        try:
            table = sheet_tabs.currentWidget()
            if not table:
                log(t("no_active_sheet"), "orange")
                return

            sheet_name = sheet_tabs.tabText(sheet_tabs.currentIndex())
            data = []
            for r in range(table.rowCount()):
                row_dict = {}
                for c, field in enumerate(fields_config):
                    item = table.item(r, c)
                    row_dict[field["key"]] = item.text() if item else ""
                data.append(row_dict)

            if not data:
                log(t("no_data_to_scrape"), "orange")
                return

            scrape_service.start_scrape(sheet_name, data)
        except Exception as e:
            log(f"{t('scrape_failed')}: {str(e)}", "red")

    def on_stop_scrape():
        """停止当前抓取任务"""
        scrape_service.stop_scrape()

    btn_select_file.clicked.connect(on_select_file)
    btn_add_step.clicked.connect(on_add_step)
    btn_del_step.clicked.connect(on_del_step)
    btn_add_sheet.clicked.connect(lambda: add_sheet())
    btn_del_sheet.clicked.connect(on_del_sheet)
    btn_save.clicked.connect(on_save)
    btn_start.clicked.connect(on_start_scrape)
    btn_stop.clicked.connect(on_stop_scrape)
    btn_clear_cache.clicked.connect(scrape_service.clear_chrome_cache)
    btn_kill_processes.clicked.connect(scrape_service.kill_chrome_processes)
    if clear_log_func:
        btn_clear_logs.clicked.connect(clear_log_func)

    # 启动时加载默认文件
    log(f"{t('ready')} | {t('fields_loaded')} | {t('waiting_file')}")
    load_initial_file()
