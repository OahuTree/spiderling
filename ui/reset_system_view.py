from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QListWidget, QListWidgetItem, QMessageBox, QFrame)
from PyQt5.QtCore import Qt
from services.file_service import FileService
from services.ui_service import UIService
from services.ui_generator import UIGenerator

def create_reset_system(parent, layout, t):
    """
    创建系统重置视图，允许用户选择性地恢复初始配置文件。
    """
    base_font, title_font, btn_font, _ = UIGenerator.get_fonts()

    # 标题
    title = QLabel(t("reset_system"))
    title.setFont(title_font)
    title.setStyleSheet(UIService.get_style("title_label"))
    layout.addWidget(title)

    # 说明文字
    desc = QLabel(t("reset_confirm"))
    desc.setFont(base_font)
    desc.setWordWrap(True)
    desc.setStyleSheet("color: #86868b; margin-bottom: 20px;")
    layout.addWidget(desc)

    # 文件列表容器
    list_widget = QListWidget()
    list_widget.setFont(base_font)
    list_widget.setStyleSheet(UIService.get_style("log_area")) # 复用样式
    layout.addWidget(list_widget)

    # 获取可重置文件列表
    resetable_files = FileService.get_resetable_files()
    
    # 填充列表项
    items = []
    # 添加一个特殊的 locales 项
    locales_item = QListWidgetItem(t("locales_dir"))
    locales_item.setFlags(locales_item.flags() | Qt.ItemIsUserCheckable)
    locales_item.setCheckState(Qt.Unchecked)
    locales_item.setData(Qt.UserRole, "locales")
    list_widget.addItem(locales_item)
    items.append(locales_item)

    for f in resetable_files:
        item = QListWidgetItem(f)
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(Qt.Unchecked)
        item.setData(Qt.UserRole, f)
        list_widget.addItem(item)
        items.append(item)

    # 工具栏
    toolbar = QHBoxLayout()
    btn_all = UIGenerator.setup_button(QPushButton(t("select_all")), btn_font)
    btn_none = UIGenerator.setup_button(QPushButton(t("deselect_all")), btn_font)
    btn_reset = UIGenerator.setup_button(QPushButton(t("reset_now")), btn_font, color="#ff3b30")
    
    toolbar.addWidget(btn_all)
    toolbar.addWidget(btn_none)
    toolbar.addStretch()
    toolbar.addWidget(btn_reset)
    layout.addLayout(toolbar)

    def select_all():
        for i in items: i.setCheckState(Qt.Checked)

    def deselect_all():
        for i in items: i.setCheckState(Qt.Unchecked)

    def on_reset():
        selected = [i for i in items if i.checkState() == Qt.Checked]
        if not selected:
            return

        reply = QMessageBox.question(parent, t("reset_system"), t("reset_confirm"), 
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            success_count = 0
            failed_list = []
            
            for i in selected:
                file_id = i.data(Qt.UserRole)
                if file_id == "locales":
                    if FileService.reset_locales(): success_count += 1
                    else: failed_list.append(t("locales_dir"))
                else:
                    if FileService.reset_file(file_id): success_count += 1
                    else: failed_list.append(file_id)

            if success_count > 0:
                QMessageBox.information(parent, t("success"), f"{t('reset_success')} {success_count}")
            
            if failed_list:
                QMessageBox.warning(parent, t("error"), f"{t('reset_failed')}: {', '.join(failed_list)}")

    btn_all.clicked.connect(select_all)
    btn_none.clicked.connect(deselect_all)
    btn_reset.clicked.connect(on_reset)

    layout.addStretch()
