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
    path_config = DBService.load_path_config()
    current_config_dir = path_config.get("config_dir", "config")

    db_config = config_data["databases"][0] if config_data["databases"] else {}

    # 字体设置
    font_settings = UIService.get_font_settings()
    base_font = QFont(font_settings.get("font_family"), font_settings.get("font_size"))
    title_font = QFont(font_settings.get("font_family"), font_settings.get("title_font_size"), QFont.Bold)
    mono_font = QFont(font_settings.get("mono_family"), font_settings.get("mono_size"))

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

    def _create_input(value, is_password=False):
        edit = QLineEdit(str(value))
        edit.setFont(base_font)
        edit.setStyleSheet(input_style)
        if is_password:
            edit.setEchoMode(QLineEdit.Password)
        return edit

    def _add_input_row(label_text, value, is_password=False):
        edit = _create_input(value, is_password)
        form_layout.addRow(QLabel(label_text, font=base_font), edit)
        return edit

    config_name_input = _add_input_row(f"{t('config_name')}:", db_config.get("name", "Default"))

    # 配置目录组合控件
    config_dir_layout = QHBoxLayout()
    config_dir_input = _create_input(current_config_dir)

    btn_browse_dir = QPushButton("...")
    btn_browse_dir.setFixedWidth(40)
    btn_browse_dir.setCursor(Qt.PointingHandCursor)
    btn_browse_dir.setStyleSheet(
        "QPushButton { background-color: #e0e0e0; color: #333; border: 1px solid #d1d1d6; border-radius: 4px; } QPushButton:hover { background-color: #d1d1d6; }")

    config_dir_layout.addWidget(config_dir_input)
    config_dir_layout.addWidget(btn_browse_dir)
    form_layout.addRow(QLabel(f"{t('config_dir')}:", font=base_font), config_dir_layout)

    def on_browse_dir():
        from PyQt5.QtWidgets import QFileDialog
        dir_path = QFileDialog.getExistingDirectory(parent, t("select_config_dir"), config_dir_input.text())
        if dir_path:
            config_dir_input.setText(dir_path)

    btn_browse_dir.clicked.connect(on_browse_dir)

    db_type_combo = QComboBox()
    db_type_combo.setFont(base_font)
    db_type_combo.setStyleSheet(input_style)
    db_type_combo.addItems(["MySQL", "PostgreSQL", "SQLite", "SQL Server", "Oracle"])
    db_type_combo.setCurrentText(db_config.get("type", "SQLite"))
    form_layout.addRow(QLabel(f"{t('db_type')}:", font=base_font), db_type_combo)

    host_input = _add_input_row(f"{t('host')}:", db_config.get("host", ""))
    port_input = _add_input_row(f"{t('port')}:", db_config.get("port", ""))
    db_name_input = _add_input_row(f"{t('database')}:", db_config.get("database", "sqlitedb/craw.db"))
    user_input = _add_input_row(f"{t('username')}:", db_config.get("username", ""))
    pass_input = _add_input_row(f"{t('password')}:", db_config.get("password", ""), is_password=True)
    table_input = _add_input_row(f"{t('table_name')}:", db_config.get("table_name", ""))
    params_input = _add_input_row(f"{t('conn_params')}:", db_config.get("params", ""))

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
        if isinstance(widget, QComboBox):
            widget.currentTextChanged.connect(update_conn_string)
        else:
            widget.textChanged.connect(update_conn_string)
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
            import os
            import shutil

            # 获取原来的路径
            old_full_path = DBService.get_config_path()
            new_config_dir = config_dir_input.text().strip()
            if not new_config_dir:
                new_config_dir = "config"

            # 保存路径配置
            DBService.save_path_config(new_config_dir)
            new_full_path = DBService.get_config_path()

            # 扩展新目录路径以用于创建物理目录
            expanded_new_dir = os.path.expanduser(new_config_dir)

            # 如果路径变了，且原文件存在，则移动文件
            if old_full_path != new_full_path and os.path.exists(old_full_path):
                # 确保新目录存在
                os.makedirs(expanded_new_dir, exist_ok=True)
                # 如果目标文件已存在，则根据当前 UI 设置覆盖它
                if not os.path.exists(new_full_path):
                    shutil.move(old_full_path, new_full_path)
                else:
                    # 如果新位置已经有一个同名文件，我们根据当前 UI 设置覆盖它
                    pass

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
