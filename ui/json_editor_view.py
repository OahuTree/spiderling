import os
from PyQt5.QtWidgets import (QVBoxLayout, QHBoxLayout, QPushButton, 
                             QTabWidget, QMessageBox, QTableWidgetItem)
from PyQt5.QtGui import QFont
from ui.common_widgets import JsonTable
from services.json_service import JsonService
from services.ui_service import UIService

def create_json_editor(parent, layout, t, log_func=None):
    font_settings = UIService.get_font_settings()
    base_font = QFont(font_settings.get("font_family", "Sans Serif"), font_settings.get("font_size", 12))
    
    # helper for logging
    def log(msg, color="black"):
        if log_func:
            log_func(msg, color)

    path = os.path.join("config", "browser_config.json")
    raw_json = JsonService.load_json(path, default_data={})

    # 将平铺的配置转换为 Table 需要的列表格式
    json_data = {
        "General": [
            {"Key": "chrome_path", "Value": raw_json.get("chrome_path", "")},
            {"Key": "user_data_dir", "Value": raw_json.get("user_data_dir", "")},
            {"Key": "remote_debugging_port", "Value": raw_json.get("remote_debugging_port", 9222)},
        ],
        "Arguments": [{"Argument": arg} for arg in raw_json.get("arguments", [])],
        "Binary Locations": [{"OS": k, "Path": v} for k, v in raw_json.get("binary_locations", {}).items()]
    }

    toolbar = QHBoxLayout()
    btn_add = QPushButton(t("add_item"))
    btn_del = QPushButton(t("del_item"))
    btn_save = QPushButton(t("save_browser_config"))
    
    btn_style = UIService.get_style("button")
    for btn in [btn_add, btn_save]:
        btn.setStyleSheet(btn_style)
        btn.setFont(base_font)
        toolbar.addWidget(btn)
    
    # 删除按钮使用红色文字，在通用样式基础上替换颜色
    red_text_style = btn_style.replace("color: #1d1d1f;", "color: #ff3b30;")
    btn_del.setStyleSheet(red_text_style)
    btn_del.setFont(base_font)
    toolbar.addWidget(btn_del)
    toolbar.addStretch()
    layout.addLayout(toolbar)

    tabs = QTabWidget()
    tabs.setFont(base_font)
    tabs.setStyleSheet(UIService.get_style("sheet_tabs"))
    layout.addWidget(tabs)

    for section_name, data_list in json_data.items():
        if isinstance(data_list, list):
            table = JsonTable(data_list, t)
            tabs.addTab(table, section_name)

    def on_add():
        """
        在当前 Tab 的表格末尾添加一个新行。
        """
        try:
            table = tabs.currentWidget()
            if table:
                row = table.rowCount()
                table.insertRow(row)
                for c in range(table.columnCount()):
                    table.setItem(row, c, QTableWidgetItem(""))
        except Exception as e:
            QMessageBox.critical(parent, t("error"), f"{t('add_failed')}: {str(e)}")

    def on_del():
        """
        删除当前 Tab 中选中的行。
        """
        try:
            table = tabs.currentWidget()
            if table:
                row = table.currentRow()
                if row != -1:
                    table.removeRow(row)
        except Exception as e:
            QMessageBox.critical(parent, t("error"), f"{t('del_failed')}: {str(e)}")

    def on_save():
        """
        汇总所有 Tab 的表格数据并转换回平铺格式保存到 browser_config.json。
        """
        try:
            transformed_data = {}
            for i in range(tabs.count()):
                name = tabs.tabText(i)
                table = tabs.widget(i)
                transformed_data[name] = table.get_data()
            
            # 还原回平铺格式
            final_json = {}
            
            # General
            general_rows = transformed_data.get("General", [])
            for row in general_rows:
                key = row.get("Key")
                val = row.get("Value")
                if key == "remote_debugging_port":
                    try: val = int(val)
                    except: val = 9222
                if key:
                    final_json[key] = val
            
            # Arguments
            arg_rows = transformed_data.get("Arguments", [])
            final_json["arguments"] = [row.get("Argument") for row in arg_rows if row.get("Argument")]
            
            # Binary Locations
            loc_rows = transformed_data.get("Binary Locations", [])
            final_json["binary_locations"] = {row.get("OS"): row.get("Path") for row in loc_rows if row.get("OS")}
            
            JsonService.save_json(path, final_json)
            log(f"{t('save_browser_config_success')}: {path}", "green")
            QMessageBox.information(parent, t("success"), t("save_success"))
        except Exception as e:
            log(f"{t('save_browser_config_failed')}: {str(e)}", "red")
            QMessageBox.critical(parent, t("error"), f"{t('save_browser_config_err')}: {str(e)}")

    btn_add.clicked.connect(on_add)
    btn_del.clicked.connect(on_del)
    btn_save.clicked.connect(on_save)
