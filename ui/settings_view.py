from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QComboBox, QTextEdit, QFormLayout, 
                             QPushButton, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from services.db_service import DBService
from services.ui_service import UIService

def create_settings(parent, layout, t):
    # 加载现有配置
    config_data = DBService.load_config()
    db_config = config_data["databases"][0] if config_data["databases"] else {}

    # 字体设置
    font_settings = UIService.get_font_settings()
    base_font = QFont(font_settings.get("font_family", "Sans Serif"), font_settings.get("font_size", 12))
    
    title_font = QFont(font_settings.get("font_family", "Sans Serif"), font_settings.get("title_font_size", 22), QFont.Bold)
    
    mono_font = QFont(font_settings.get("mono_family", "Monospace"), font_settings.get("mono_size", 11))

    title = QLabel(t("db_config"))
    title.setFont(title_font)
    title.setStyleSheet(UIService.get_style("title_label"))
    layout.addWidget(title)

    container = QWidget()
    container.setMaximumWidth(700)
    form_layout = QFormLayout(container)
    form_layout.setLabelAlignment(Qt.AlignRight)
    form_layout.setSpacing(20)

    input_style = UIService.get_style("input_field")
    
    config_name_input = QLineEdit(db_config.get("name", "Default"))
    config_name_input.setFont(base_font)
    config_name_input.setStyleSheet(input_style)
    form_layout.addRow(QLabel(f"{t('config_name')}:", font=base_font), config_name_input)

    db_type_combo = QComboBox()
    db_type_combo.setFont(base_font)
    db_type_combo.setStyleSheet(input_style)
    db_type_combo.addItems(["MySQL", "PostgreSQL", "SQLite", "SQL Server", "Oracle"])
    db_type_combo.setCurrentText(db_config.get("type", "SQLite"))
    form_layout.addRow(QLabel(f"{t('db_type')}:", font=base_font), db_type_combo)

    host_input = QLineEdit(db_config.get("host", ""))
    host_input.setFont(base_font)
    host_input.setStyleSheet(input_style)
    form_layout.addRow(QLabel(f"{t('host')}:", font=base_font), host_input)

    port_input = QLineEdit(db_config.get("port", ""))
    port_input.setFont(base_font)
    port_input.setStyleSheet(input_style)
    form_layout.addRow(QLabel(f"{t('port')}:", font=base_font), port_input)

    db_name_input = QLineEdit(db_config.get("database", "sqlitedb/craw.db"))
    db_name_input.setFont(base_font)
    db_name_input.setStyleSheet(input_style)
    form_layout.addRow(QLabel(f"{t('database')}:", font=base_font), db_name_input)

    user_input = QLineEdit(db_config.get("username", ""))
    user_input.setFont(base_font)
    user_input.setStyleSheet(input_style)
    form_layout.addRow(QLabel(f"{t('username')}:", font=base_font), user_input)

    pass_input = QLineEdit(db_config.get("password", ""))
    pass_input.setFont(base_font)
    pass_input.setStyleSheet(input_style)
    pass_input.setEchoMode(QLineEdit.Password)
    form_layout.addRow(QLabel(f"{t('password')}:", font=base_font), pass_input)

    table_input = QLineEdit(db_config.get("table_name", ""))
    table_input.setFont(base_font)
    table_input.setStyleSheet(input_style)
    form_layout.addRow(QLabel(f"{t('table_name')}:", font=base_font), table_input)

    params_input = QLineEdit(db_config.get("params", ""))
    params_input.setFont(base_font)
    params_input.setStyleSheet(input_style)
    form_layout.addRow(QLabel(f"{t('conn_params')}:", font=base_font), params_input)

    conn_string_text = QTextEdit()
    conn_string_text.setFont(mono_font)
    conn_string_text.setFixedHeight(100)
    conn_string_text.setReadOnly(True)
    conn_string_text.setStyleSheet(UIService.get_style("conn_string_area"))
    form_layout.addRow(QLabel(f"{t('conn_string')}:", font=base_font), conn_string_text)
    layout.addWidget(container, 0, Qt.AlignHCenter)

    def update_conn_string():
        conn_str = DBService.generate_conn_string(
            db_type_combo.currentText(), host_input.text(), port_input.text(),
            db_name_input.text(), user_input.text(), pass_input.text(),
            params_input.text()
        )
        conn_string_text.setPlainText(conn_str)

    for widget in [db_type_combo, host_input, port_input, db_name_input, user_input, pass_input, params_input]:
        if isinstance(widget, QComboBox): widget.currentTextChanged.connect(update_conn_string)
        else: widget.textChanged.connect(update_conn_string)
    update_conn_string()

    btn_layout = QHBoxLayout()
    btn_layout.addStretch()
    btn_test = QPushButton(t("test_conn"))
    btn_ok = QPushButton(t("ok"))
    btn_cancel = QPushButton(t("cancel"))
    
    styled_btn_qss = UIService.get_style("button")
    
    for btn in [btn_test, btn_ok, btn_cancel]:
        btn.setFont(base_font)
        btn.setStyleSheet(styled_btn_qss)
        btn_layout.addWidget(btn)
        btn_layout.addSpacing(10)
    
    btn_layout.addStretch()
    layout.addLayout(btn_layout)
    layout.addStretch()

    def on_test_conn():
        """
        测试当前填写的数据库连接配置。
        """
        conn_str = conn_string_text.toPlainText()
        table_name = table_input.text()
        
        success, msg = DBService.test_connection(conn_str, table_name)
        if success:
            QMessageBox.information(parent, t("success"), msg)
        else:
            QMessageBox.warning(parent, t("error"), msg)

    btn_test.clicked.connect(on_test_conn)

    def on_cancel():
        # 尝试通过寻找父 TabWidget 来关闭当前页
        widget = parent
        while widget:
            from PyQt5.QtWidgets import QTabWidget
            if isinstance(widget, QTabWidget):
                idx = widget.indexOf(parent)
                if idx != -1:
                    widget.removeTab(idx)
                    return
            widget = widget.parent()

    btn_cancel.clicked.connect(on_cancel)

    def save_config():
        """
        保存数据库配置到 JSON 文件。
        """
        try:
            config = DBService.load_config()
            new_db = {
                "id": db_config.get("id", "default"),  # 保持原有 ID
                "name": config_name_input.text(),
                "type": db_type_combo.currentText(),
                "host": host_input.text(),
                "port": port_input.text(),
                "database": db_name_input.text(),
                "username": user_input.text(),
                "password": pass_input.text(),
                "table_name": table_input.text(),
                "params": params_input.text()
            }
            config["databases"] = [new_db]
            DBService.save_config(config)
            QMessageBox.information(parent, t("success"), t("save_success"))
        except Exception as e:
            QMessageBox.critical(parent, t("error"), f"{t('save_db_config_err')}: {str(e)}")

    btn_ok.clicked.connect(save_config)
