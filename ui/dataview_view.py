from PyQt5.QtWidgets import (QLabel, QLineEdit, QComboBox, QPushButton, QTableWidget, 
                             QTableWidgetItem, QMessageBox, QHeaderView, QHBoxLayout)
from services.ui_service import UIService
from services.db_service import DBService
from services.ui_generator import UIGenerator

def create_dataview(parent, layout, t):
    """
    创建数据查看视图。
    参数:
        parent: 父窗口组件
        layout: 布局管理器
        t: 翻译函数
    """
    # 获取通用的字体设置
    base_font, title_font, _, _ = UIGenerator.get_fonts()
    
    # 从数据库配置中加载默认表名
    config_data = DBService.load_config()
    default_table = config_data["databases"][0].get("table_name", "") if config_data["databases"] else ""

    # 设置界面标题
    title = QLabel(t("data_center"))
    title.setFont(title_font)
    title.setStyleSheet(UIService.get_style("title_label"))
    layout.addWidget(title)
    
    # 构建查询工具栏
    toolbar = QHBoxLayout()
    toolbar.setSpacing(15)
    
    def add_widget_with_label(label_text, widget):
        if label_text:
            toolbar.addWidget(QLabel(label_text, font=base_font))
        toolbar.addWidget(UIGenerator.setup_input(widget, base_font))

    # 表名输入框
    table_input = QLineEdit(default_table)
    table_input.setFixedWidth(200)
    add_widget_with_label(f"{t('table_name')}:", table_input)
    
    # 查询行数限制输入
    limit_input = QLineEdit("100")
    limit_input.setFixedWidth(80)
    add_widget_with_label(f"{t('limit_rows')}:", limit_input)
    
    # 排序字段选择
    field_combo = QComboBox()
    field_combo.setFixedWidth(150)
    add_widget_with_label(f"{t('sort_field')}:", field_combo)
    
    # 排序顺序选择 (升序/降序)
    order_combo = QComboBox()
    order_combo.addItems(["ASC", "DESC"])
    order_combo.setFixedWidth(80)
    add_widget_with_label("", order_combo)
    
    # 执行查询按钮
    btn_query = UIGenerator.setup_button(QPushButton(t("query")), base_font)
    toolbar.addWidget(btn_query)
    toolbar.addStretch()
    layout.addLayout(toolbar)
    
    # 数据展示表格初始化
    table = QTableWidget()
    table.setFont(base_font)
    table.horizontalHeader().setFont(base_font)
    table.setStyleSheet(UIService.get_style("table"))
    table.setAlternatingRowColors(True)
    layout.addWidget(table)

    def refresh_fields():
        """根据输入的表名动态刷新可用的字段列表"""
        table_name = table_input.text().strip()
        if table_name:
            columns = DBService.get_table_columns(table_name)
            field_combo.clear()
            field_combo.addItem("")
            if columns: field_combo.addItems(columns)

    # 监听表名输入完成事件，自动刷新字段
    table_input.editingFinished.connect(refresh_fields)
    
    def on_query():
        """执行数据库查询并将结果显示在表格中"""
        table_name = table_input.text().strip()
        if not table_name:
            return QMessageBox.warning(parent, t("warning"), t("input_table_name_tip"))
            
        try:
            limit = int(limit_input.text().strip())
        except: limit = 100
            
        # 调用数据库服务获取数据
        df, msg = DBService.fetch_data(table_name, limit, field_combo.currentText(), order_combo.currentText())
        if df is not None:
            # 清空现有表格并设置列头
            table.setRowCount(0)
            table.setColumnCount(len(df.columns))
            table.setHorizontalHeaderLabels(df.columns)
            
            # 填充数据内容
            for i, row in df.iterrows():
                table.insertRow(i)
                for j, val in enumerate(row):
                    table.setItem(i, j, QTableWidgetItem(str(val) if val is not None else ""))
            
            # 自动调整列宽以适应内容
            table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        else:
            QMessageBox.critical(parent, t("error"), f"{t('query_failed')}: {msg}")

    # 绑定查询按钮点击事件
    btn_query.clicked.connect(on_query)
    
    # 页面加载时初始运行一次字段刷新
    refresh_fields()
