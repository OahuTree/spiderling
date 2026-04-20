from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QComboBox, QPushButton, QTableWidget, 
                             QTableWidgetItem, QMessageBox, QHeaderView)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from services.ui_service import UIService
from services.db_service import DBService

def create_dataview(parent, layout, t):
    font_settings = UIService.get_font_settings()
    base_font = QFont(font_settings.get("font_family", "Sans Serif"), font_settings.get("font_size", 12))
    title_font = QFont(font_settings.get("font_family", "Sans Serif"), font_settings.get("title_font_size", 22), QFont.Bold)
    
    # 获取默认配置中的表名
    config_data = DBService.load_config()
    default_table = config_data["databases"][0].get("table_name", "") if config_data["databases"] else ""

    # 标题
    title = QLabel(t("data_center"))
    title.setFont(title_font)
    title.setStyleSheet(UIService.get_style("title_label"))
    layout.addWidget(title)
    
    # 查询工具栏
    toolbar = QHBoxLayout()
    toolbar.setSpacing(15)
    
    input_style = UIService.get_style("input_field")
    btn_style = UIService.get_style("button")

    # 表名输入
    toolbar.addWidget(QLabel(f"{t('table_name')}:", font=base_font))
    table_input = QLineEdit(default_table)
    table_input.setFont(base_font)
    table_input.setStyleSheet(input_style)
    table_input.setFixedWidth(200)
    toolbar.addWidget(table_input)
    
    # 行数输入
    toolbar.addWidget(QLabel(f"{t('limit_rows')}:", font=base_font))
    limit_input = QLineEdit("100")
    limit_input.setFont(base_font)
    limit_input.setStyleSheet(input_style)
    limit_input.setFixedWidth(80)
    toolbar.addWidget(limit_input)
    
    # 排序字段
    toolbar.addWidget(QLabel(f"{t('sort_field')}:", font=base_font))
    field_combo = QComboBox()
    field_combo.setFont(base_font)
    field_combo.setStyleSheet(input_style)
    field_combo.setFixedWidth(150)
    toolbar.addWidget(field_combo)
    
    # 排序顺序
    order_combo = QComboBox()
    order_combo.setFont(base_font)
    order_combo.setStyleSheet(input_style)
    order_combo.addItems(["ASC", "DESC"])
    order_combo.setFixedWidth(80)
    toolbar.addWidget(order_combo)
    
    # 查询按钮
    btn_query = QPushButton(t("query"))
    btn_query.setFont(base_font)
    btn_query.setStyleSheet(btn_style)
    toolbar.addWidget(btn_query)
    
    toolbar.addStretch()
    layout.addLayout(toolbar)
    layout.addSpacing(10)
    
    # 数据展示表格
    table = QTableWidget()
    table.setFont(base_font)
    table.horizontalHeader().setFont(base_font)
    table.setStyleSheet(UIService.get_style("table"))
    table.setAlternatingRowColors(True)
    layout.addWidget(table)

    def refresh_fields():
        """根据表名刷新字段列表"""
        table_name = table_input.text().strip()
        if not table_name: return
        
        columns = DBService.get_table_columns(table_name)
        field_combo.clear()
        field_combo.addItem("") # 允许不排序
        if columns:
            field_combo.addItems(columns)

    table_input.editingFinished.connect(refresh_fields)
    
    def on_query():
        """执行查询逻辑"""
        table_name = table_input.text().strip()
        limit_str = limit_input.text().strip()
        sort_field = field_combo.currentText()
        sort_order = order_combo.currentText()
        
        if not table_name:
            QMessageBox.warning(parent, t("warning"), t("input_table_name_tip"))
            return
            
        try:
            limit = int(limit_str)
        except:
            limit = 100
            
        df, msg = DBService.fetch_data(table_name, limit, sort_field, sort_order)
        
        if df is not None:
            # 更新表格展示
            table.setRowCount(0)
            table.setColumnCount(len(df.columns))
            table.setHorizontalHeaderLabels(df.columns)
            
            for i, row in df.iterrows():
                table.insertRow(i)
                for j, value in enumerate(row):
                    table.setItem(i, j, QTableWidgetItem(str(value) if value is not None else ""))
            
            # 自动调整列宽
            table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        else:
            QMessageBox.critical(parent, t("error"), f"{t('query_failed')}: {msg}")

    btn_query.clicked.connect(on_query)
    
    # 初始刷新字段
    refresh_fields()
