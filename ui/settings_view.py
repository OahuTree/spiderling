from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QComboBox, QTextEdit, QFormLayout,
                             QPushButton, QMessageBox, QTabWidget)
from PyQt5.QtCore import Qt
from services.db_service import DBService
from services.ui_service import UIService
from services.ui_generator import UIGenerator

def create_settings(parent, layout, t):
    """
    创建系统配置（数据库设置）视图。
    参数:
        parent: 父窗口组件
        layout: 布局管理器
        t: 翻译函数
    """
    # 初始化字体和加载现有数据库配置
    base_font, title_font, btn_font, mono_font = UIGenerator.get_fonts()
    config_data = DBService.load_config()
    db_config = config_data["databases"][0] if config_data["databases"] else {}

    # 设置界面标题
    title = QLabel(t("db_config"))
    title.setFont(title_font)
    title.setStyleSheet(UIService.get_style("title_label"))
    layout.addWidget(title)

    # 创建中心表单布局，并限制最大宽度以保持整洁
    container = QWidget()
    container.setMaximumWidth(700)
    form_layout = QFormLayout(container)
    form_layout.setLabelAlignment(Qt.AlignRight)
    form_layout.setSpacing(20)

    def _add_input_row(label_text, value, is_password=False):
        """
        向表单添加一行输入，包含标签和输入框。
        """
        edit = UIGenerator.setup_input(QLineEdit(str(value)), base_font)
        if is_password: edit.setEchoMode(QLineEdit.Password)
        form_layout.addRow(QLabel(label_text, font=base_font), edit)
        return edit

    # 添加基本配置项
    config_name_input = _add_input_row(f"{t('config_name')}:", db_config.get("name", "Default"))
    db_type_combo = UIGenerator.setup_input(QComboBox(), base_font)
    db_type_combo.addItems(["MySQL", "PostgreSQL", "SQLite", "SQL Server", "Oracle"])
    db_type_combo.setCurrentText(db_config.get("type", "SQLite"))
    form_layout.addRow(QLabel(f"{t('db_type')}:", font=base_font), db_type_combo)

    # 定义具体的连接参数输入框
    inputs = {
        "host": _add_input_row(f"{t('host')}:", db_config.get("host", "")),
        "port": _add_input_row(f"{t('port')}:", db_config.get("port", "")),
        "database": _add_input_row(f"{t('database')}:", db_config.get("database", ".sqlitedb/spiderling.db")),
        "username": _add_input_row(f"{t('username')}:", db_config.get("username", "")),
        "password": _add_input_row(f"{t('password')}:", db_config.get("password", ""), True),
        "table": _add_input_row(f"{t('table_name')}:", db_config.get("table_name", "")),
        "params": _add_input_row(f"{t('conn_params')}:", db_config.get("params", ""))
    }

    # 连接字符串预览区域（只读）
    conn_string_text = QTextEdit()
    conn_string_text.setFont(mono_font)
    conn_string_text.setFixedHeight(100)
    conn_string_text.setReadOnly(True)
    conn_string_text.setStyleSheet(UIService.get_style("conn_string_area"))
    form_layout.addRow(QLabel(f"{t('conn_string')}:", font=base_font), conn_string_text)
    
    # 居中添加容器到主布局
    layout.addWidget(container, 0, Qt.AlignHCenter)

    def update_conn_string():
        """根据当前输入动态更新连接字符串预览"""
        conn_str = DBService.generate_conn_string(
            db_type_combo.currentText(), inputs["host"].text(), inputs["port"].text(),
            inputs["database"].text(), inputs["username"].text(), inputs["password"].text(),
            inputs["params"].text()
        )
        conn_string_text.setPlainText(conn_str)

    # 为所有输入框绑定变化事件
    for w in [db_type_combo] + list(inputs.values()):
        if isinstance(w, QComboBox): w.currentTextChanged.connect(update_conn_string)
        else: w.textChanged.connect(update_conn_string)
    
    # 初始刷新预览
    update_conn_string()

    # 底部按钮栏
    btn_layout = QHBoxLayout()
    btn_layout.addStretch()
    btns = {
        "test": UIGenerator.setup_button(QPushButton(t("test_conn")), base_font),
        "ok": UIGenerator.setup_button(QPushButton(t("ok")), base_font),
        "cancel": UIGenerator.setup_button(QPushButton(t("cancel")), base_font)
    }
    for b in btns.values():
        btn_layout.addWidget(b)
        btn_layout.addSpacing(10)
    btn_layout.addStretch()
    layout.addLayout(btn_layout)
    layout.addStretch()

    def on_test():
        """测试数据库连接有效性"""
        success, msg = DBService.test_connection(conn_string_text.toPlainText(), inputs["table"].text())
        (QMessageBox.information if success else QMessageBox.warning)(parent, t("success") if success else t("error"), msg)

    def on_cancel():
        """关闭当前配置页签"""
        w = parent
        while w:
            if isinstance(w, QTabWidget):
                idx = w.indexOf(parent)
                if idx != -1: return w.removeTab(idx)
            w = w.parent()

    def save_config():
        """将当前配置保存回 db_config.json"""
        try:
            config = DBService.load_config()
            config["databases"] = [{
                "id": db_config.get("id", "default"),
                "name": config_name_input.text(),
                "type": db_type_combo.currentText(),
                **{k: v.text() for k, v in inputs.items()},
                "database": inputs["database"].text(), # 特殊处理映射
                "table_name": inputs["table"].text()
            }]
            DBService.save_config(config)
            QMessageBox.information(parent, t("success"), t("save_success"))
        except Exception as e:
            # 异常处理，弹窗并记录
            UIGenerator.handle_exception(parent, t, e, prefix=t('save_db_config_err'))

    # 连接按钮信号
    btns["test"].clicked.connect(on_test)
    btns["cancel"].clicked.connect(on_cancel)
    btns["ok"].clicked.connect(save_config)
