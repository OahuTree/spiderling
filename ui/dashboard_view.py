import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTabWidget, QFileDialog, QDialog,
                             QLineEdit, QInputDialog, QFrame, QTableWidgetItem,
                             QMessageBox, QStyle, QCheckBox)
from PyQt5.QtCore import Qt
from ui.common_widgets import ExcelTable, StepDialog
from services.file_service import FileService
from services.scrape_service import ScrapeService
from services.ui_service import UIService
from services.ui_generator import UIGenerator

def create_dashboard(parent, layout, t, log_func=None, clear_log_func=None, lang="zh"):
    """
    创建主仪表盘视图，负责任务配置（Excel 编辑）和抓取控制。
    """
    # 初始化字体和日志函数
    base_font, title_font, btn_font, _ = UIGenerator.get_fonts()
    def log(msg, color="black"):
        if log_func: log_func(msg, color)

    # 初始化抓取服务并注册清理逻辑
    scrape_service = ScrapeService(log_func=log, t=t)
    parent.cleanup = lambda: scrape_service.stop_scrape()

    # 加载字段配置定义
    fields_path = FileService.get_config_path("fields.json")
    fields_config = FileService.load_json(fields_path).get("fields", [])

    # 添加装饰性横线
    def add_line():
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #e0e0e0; margin: 10px 0;")
        layout.addWidget(line)
    add_line()

    # 文件选择区域
    file_layout = QHBoxLayout()
    file_label = QLabel(f"{t('current_file')}: {t('no_file')}", font=base_font)
    btn_select_file = UIGenerator.setup_button(QPushButton(t("select_excel")), btn_font)
    file_layout.addWidget(file_label)
    file_layout.addWidget(btn_select_file)
    file_layout.addStretch()
    layout.addLayout(file_layout)

    # 任务配置工具栏（Sheet 和 步骤 的增删改）
    toolbar = QHBoxLayout()
    def setup_btn(text, color=None, style="button"):
        btn = UIGenerator.setup_button(QPushButton(text), btn_font, style_key=style, color=color)
        toolbar.addWidget(btn)
        return btn

    btn_add_step = setup_btn(t("add_step"))
    btn_del_step = setup_btn(t("del_step"), "#ff3b30")
    btn_add_sheet = setup_btn(t("add_sheet"))
    btn_del_sheet = setup_btn(t("del_sheet"), "#ff3b30")
    btn_save = setup_btn(t("save_steps"))

    # 锁定列表拖拽的开关
    cb_disable_drag = QCheckBox(t("disable_drag"), font=base_font)
    cb_disable_drag.setChecked(True)
    toolbar.addWidget(cb_disable_drag)
    toolbar.addStretch()
    layout.addLayout(toolbar)

    # 多页签 Excel 表格编辑器区域
    tabs = QTabWidget(font=base_font)
    tabs.setStyleSheet(UIService.get_style("sheet_tabs"))
    tabs.tabBar().setExpanding(False)
    tabs.tabBar().setProperty("alignment", Qt.AlignLeft)
    layout.addWidget(tabs)

    # 运行控制工具栏（启动、停止、清理等）
    scrape_bar = QHBoxLayout()
    def add_scrape_btn(text, icon, color, callback):
        btn = UIGenerator.setup_button(QPushButton(text), btn_font, color="black")
        btn.setIcon(UIGenerator.get_colored_icon(parent, icon, color))
        btn.clicked.connect(callback)
        scrape_bar.addWidget(btn)
        return btn

    add_scrape_btn(t("start_scrape"), QStyle.SP_MediaPlay, "#34c759", lambda: on_start())
    add_scrape_btn(t("stop_scrape"), QStyle.SP_MediaStop, "#ff3b30", scrape_service.stop_scrape)
    add_scrape_btn(t("clear_chrome_cache"), QStyle.SP_TrashIcon, "#007aff", scrape_service.clear_chrome_cache)
    add_scrape_btn(t("kill_chrome_processes"), QStyle.SP_BrowserStop, "#ff9500", scrape_service.kill_chrome_processes)
    if clear_log_func: add_scrape_btn(t("clear_logs"), QStyle.SP_DialogResetButton, "#5856d6", clear_log_func)

    scrape_bar.addStretch()
    layout.addLayout(scrape_bar)

    # 动态切换表格拖拽使能状态
    cb_disable_drag.stateChanged.connect(lambda s: [tabs.widget(i)._set_drag_enabled(s == Qt.Unchecked) for i in range(tabs.count()) if hasattr(tabs.widget(i), "_set_drag_enabled")])

    # 当前打开的文件路径状态
    current_file = [None]

    def load_initial():
        """加载初始默认配置文件"""
        path = os.path.join(FileService.get_app_home(), "scraping_config_example.xlsx")
        FileService.ensure_excel_template(path, fields_config, t)
        current_file[0] = path
        file_label.setText(f"{t('current_file')}: {os.path.basename(path)}")
        data = FileService.load_excel(path, fields_config)
        tabs.clear()
        if data:
            for name, rows in data.items(): add_sheet(name, rows, silent=True)
        else: add_sheet("ScrapingSteps", silent=True)

    def do_save():
        """执行静默保存到当前 Excel 文件"""
        if not current_file[0]: return
        data = {tabs.tabText(i): [[tabs.widget(i).item(r, c).text() if tabs.widget(i).item(r, c) else "" for c in range(tabs.widget(i).columnCount())] for r in range(tabs.widget(i).rowCount())] for i in range(tabs.count())}
        FileService.save_excel(current_file[0], data, fields_config, t)

    def add_sheet(name=None, rows=None, silent=False):
        """添加一个新的 Excel Sheet 页签"""
        if name is None:
            name, ok = QInputDialog.getText(parent, t("new_sheet"), f"{t('input_sheet_name')}:", QLineEdit.Normal, f"Sheet{tabs.count() + 1}")
            if not(ok and name): return
        table = ExcelTable(fields_config, t, lang=lang)
        if hasattr(table, "_set_drag_enabled"): table._set_drag_enabled(not cb_disable_drag.isChecked())
        table.setFont(base_font)
        if rows:
            for r, row in enumerate(rows):
                table.insertRow(r)
                for c, val in enumerate(row): table.setItem(r, c, QTableWidgetItem(str(val) if val is not None else ""))
            table.on_data_structure_changed()
        # 绑定双击编辑事件
        table.cellDoubleClicked.connect(lambda r, c: on_edit(table, r))
        tabs.addTab(table, name)
        tabs.setCurrentWidget(table)
        if not silent: do_save()

    def on_edit(table, row):
        """双击行弹出对话框编辑步骤细节"""
        try:
            data = [table.item(row, c).text() if table.item(row, c) else "" for c in range(table.columnCount())]
            dialog = StepDialog(parent, fields_config, t, initial_data=data, lang=lang)
            if dialog.exec_() == QDialog.Accepted:
                for c, v in enumerate(dialog.get_data()): table.setItem(row, c, QTableWidgetItem(str(v)))
                table.on_data_structure_changed()
                do_save()
        except Exception as e: UIGenerator.handle_exception(parent, t, e, log, t('update_step_err'))

    def on_select():
        """打开文件选择对话框手动选择 Excel 配置文件"""
        path, _ = QFileDialog.getOpenFileName(parent, t("select_excel"), "", "Excel Files (*.xlsx *.xls)")
        if path:
            current_file[0], data = path, FileService.load_excel(path, fields_config)
            file_label.setText(f"{t('current_file')}: {os.path.basename(path)}")
            tabs.clear()
            for name, rows in data.items(): add_sheet(name, rows, silent=True)

    def on_action(action_func):
        """执行针对当前活动表格的原子操作"""
        try:
            table = tabs.currentWidget()
            if table: action_func(table)
        except Exception as e: UIGenerator.handle_exception(parent, t, e, log)

    def on_start():
        """启动抓取逻辑：提取当前 Sheet 数据并传递给抓取服务"""
        table = tabs.currentWidget()
        if not table: return log(t("no_active_sheet"), "orange")
        data = [{f["key"]: (table.item(r, c).text() if table.item(r, c) else "") for c, f in enumerate(fields_config)} for r in range(table.rowCount())]
        if not data: return log(t("no_data_to_scrape"), "orange")
        scrape_service.start_scrape(tabs.tabText(tabs.currentIndex()), data)

    # 绑定工具栏按钮事件
    btn_select_file.clicked.connect(on_select)
    
    def on_add_step_complex(table):
        """处理添加步骤的复杂逻辑（弹出对话框 -> 插入行）"""
        if not table: return
        d = StepDialog(parent, fields_config, t, lang=lang)
        if d.exec_() == QDialog.Accepted:
            row, data = table.rowCount(), d.get_data()
            table.insertRow(row)
            for c, v in enumerate(data): table.setItem(row, c, QTableWidgetItem(str(v)))
            table.on_data_structure_changed(); do_save()

    btn_add_step.clicked.connect(lambda: on_add_step_complex(tabs.currentWidget()))
    btn_del_step.clicked.connect(lambda: on_action(lambda tbl: tbl.currentRow() != -1 and (tbl.removeRow(tbl.currentRow()) or tbl.on_data_structure_changed() or do_save())))
    btn_add_sheet.clicked.connect(lambda: add_sheet())
    btn_del_sheet.clicked.connect(lambda: tabs.currentIndex() != -1 and (tabs.removeTab(tabs.currentIndex()) or do_save()))
    
    def on_save_btn():
        """保存按钮点击事件（含另存为逻辑）"""
        if not current_file[0]:
            path, _ = QFileDialog.getSaveFileName(parent, t("save_steps"), "steps.xlsx", "Excel Files (*.xlsx)")
            if not path: return
            current_file[0] = path
            file_label.setText(f"{t('current_file')}: {os.path.basename(path)}")
        do_save()
        QMessageBox.information(parent, t("success"), t("save_success"))

    btn_save.clicked.connect(on_save_btn)

    # 仪表盘加载完成
    log(f"{t('ready')} | {t('fields_loaded')} | {t('waiting_file')}")
    load_initial()
