import os
from PyQt5.QtWidgets import (QVBoxLayout, QHBoxLayout, QPushButton, 
                             QTabWidget, QMessageBox, QTableWidgetItem)
from services.file_service import FileService
from ui.common_widgets import JsonTable
from services.json_service import JsonService
from services.ui_service import UIService
from services.ui_generator import UIGenerator

def create_json_editor(parent, layout, t, log_func=None, item=None):
    """
    创建并初始化 JSON 编辑器视图。
    参数:
        parent: 父窗口组件
        layout: 布局管理器
        t: 翻译函数
        log_func: 日志输出函数
        item: 选中的菜单项，可包含文件路径信息
    """
    # 获取界面字体设置
    base_font, _, _, _ = UIGenerator.get_fonts()
    
    # 日志输出辅助函数
    def log(msg, color="black"):
        if log_func: log_func(msg, color)

    # 确定要编辑的 JSON 文件路径
    path = FileService.get_config_path("browser_config.json")
    if item and "file" in item: path = item["file"]
    
    # 加载 JSON 内容
    raw_json = JsonService.load_json(path, default_data={})

    # 将 JSON 数据结构化为表格显示的字典格式
    json_data = {
        "General": [
            {"Key": "chrome_path", "Value": raw_json.get("chrome_path", "")},
            {"Key": "user_data_dir", "Value": raw_json.get("user_data_dir", "")},
            {"Key": "remote_debugging_port", "Value": raw_json.get("remote_debugging_port", 9222)},
        ],
        "Arguments": [{"Argument": arg} for arg in raw_json.get("arguments", [])],
        "Binary Locations": [{"OS": k, "Path": v} for k, v in raw_json.get("binary_locations", {}).items()]
    }

    # 创建顶部工具栏（添加、删除、保存按钮）
    toolbar = QHBoxLayout()
    btn_add = UIGenerator.setup_button(QPushButton(t("add_item")), base_font)
    btn_del = UIGenerator.setup_button(QPushButton(t("del_item")), base_font, color="#ff3b30")
    btn_save = UIGenerator.setup_button(QPushButton(t("save_browser_config")), base_font)
    
    # 填充工具栏
    for btn in [btn_add, btn_save, btn_del]: toolbar.addWidget(btn)
    toolbar.addStretch()
    layout.addLayout(toolbar)

    # 创建多页签容器用于分范畴编辑 JSON 数据
    tabs = QTabWidget()
    tabs.setFont(base_font)
    tabs.setStyleSheet(UIService.get_style("sheet_tabs"))
    layout.addWidget(tabs)

    # 根据 json_data 初始化各个页签及表格
    for section_name, data_list in json_data.items():
        if isinstance(data_list, list): tabs.addTab(JsonTable(data_list, t), section_name)

    def on_add():
        """在当前选中的页签表格中添加新行"""
        table = tabs.currentWidget()
        if table:
            row = table.rowCount()
            table.insertRow(row)
            for c in range(table.columnCount()): table.setItem(row, c, QTableWidgetItem(""))

    def on_del():
        """删除当前选中的行"""
        table = tabs.currentWidget()
        if table and table.currentRow() != -1: table.removeRow(table.currentRow())

    def on_save():
        """收集所有页签的数据，转换回 JSON 格式并保存到文件"""
        try:
            # 将所有页签中的表格数据提取为字典
            transformed_data = {tabs.tabText(i): tabs.widget(i).get_data() for i in range(tabs.count())}
            
            # 手动执行从表格数据到最终 JSON 格式的逆向转换逻辑
            final_json = {}
            for row in transformed_data.get("General", []):
                key, val = row.get("Key"), row.get("Value")
                if key == "remote_debugging_port":
                    try: val = int(val)
                    except: val = 9222
                if key: final_json[key] = val
            
            # 转换 Arguments 列表
            final_json["arguments"] = [row.get("Argument") for row in transformed_data.get("Arguments", []) if row.get("Argument")]
            
            # 转换 Binary Locations 字典
            final_json["binary_locations"] = {row.get("OS"): row.get("Path") for row in transformed_data.get("Binary Locations", []) if row.get("OS")}
            
            # 执行保存
            JsonService.save_json(path, final_json)
            log(f"{t('save_browser_config_success')}: {path}", "green")
            QMessageBox.information(parent, t("success"), t("save_success"))
        except Exception as e:
            # 发生异常时显示警告并输出日志
            UIGenerator.handle_exception(parent, t, e, log, t('save_browser_config_failed'))

    # 绑定工具栏按钮事件
    btn_add.clicked.connect(on_add)
    btn_del.clicked.connect(on_del)
    btn_save.clicked.connect(on_save)
