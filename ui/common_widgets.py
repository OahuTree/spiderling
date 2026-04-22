import os
from PyQt5.QtWidgets import (QTableWidget, QTableWidgetItem, QDialog, QVBoxLayout,
                             QFormLayout, QComboBox, QSpinBox, QLineEdit, QDialogButtonBox,
                             QMenu, QApplication, QLabel, QTextEdit, QScrollArea, QWidget,
                             QSizePolicy)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from services.file_service import FileService
from services.ui_service import UIService


class NoWheelSpinBox(QSpinBox):
    """禁止鼠标滚轴使用"""

    def wheelEvent(self, event):
        event.ignore()


class NoWheelComboBox(QComboBox):
    """禁止鼠标滚轴使用"""

    def wheelEvent(self, event):
        event.ignore()


class StepDialog(QDialog):
    """
    步聚详情编辑对话框。
    根据配置动态生成输入控件，并支持根据动作类型隐藏/显示相关字段。
    """

    def __init__(self, parent, fields, t, initial_data=None, lang="zh"):
        super().__init__(parent)
        self.setWindowTitle(t("step_detail"))
        self.fields = fields
        self.t = t
        self.lang = lang
        self.inputs = {}
        self.field_rows = {}  # 存储 key -> (label, widget) 用于显隐控制
        self.actions_config = {}  # 存储动作与字段的对应关系

        # 字体初始化
        font_settings = UIService.get_font_settings()
        self.base_font = QFont(font_settings.get("font_family", "Sans Serif"), font_settings.get("font_size", 12))
        self.setFont(self.base_font)

        self.setup_ui(initial_data)

    def setup_ui(self, initial_data):
        """
        构建对话框界面。
        """
        self.resize(700, 700)  # 稍微减小初始高度
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # 滚动区域支持长表单
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll_content = QWidget()

        # 使用 QVBoxLayout 作为容器，内部放 FormLayout 和 Stretch
        # 这样可以确保 FormLayout 始终置顶，不会因为窗口拉大而导致行间距变大
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        form_layout = QFormLayout()
        self.form_layout = form_layout
        form_layout.setSpacing(12)  # 稍微减小间距
        form_layout.setLabelAlignment(Qt.AlignRight)

        content_layout.addLayout(form_layout)
        content_layout.addStretch()  # 关键：将所有内容推向顶部

        # 遍历字段生成控件
        for i, field in enumerate(self.fields):
            key = field.get("key")
            label_text = self._get_label_text(field)

            label = QLabel(label_text + ":")
            label.setFont(self.base_font)

            widget = self._create_input_widget(field, initial_data, i if initial_data else None)

            form_layout.addRow(label, widget)
            self.inputs[key] = widget
            # 记录行索引，用于控制显隐
            self.field_rows[key] = (label, widget, i)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        # 初始显隐控制
        if "action" in self.inputs:
            # 使用 currentData 获取动作的 key 而非显示文字
            action_key = self.inputs["action"].currentData()
            self.update_fields_visibility(action_key)

        # 底部按钮
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        font_settings = UIService.get_font_settings()
        btn_font = QFont(font_settings.get("font_family", "Sans Serif"), font_settings.get("btn_font_size", 14))
        buttons.setFont(btn_font)
        buttons.setStyleSheet(UIService.get_style("dialog_buttons"))

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _get_label_text(self, field):
        """
        从字段配置中获取国际化标签文本。
        """
        key = field.get("key")
        i18n_key = field.get("i18n_key")

        if i18n_key:
            label_text = self.t(i18n_key)
        else:
            label_obj = field.get("label", {})
            if isinstance(label_obj, dict):
                label_text = label_obj.get(self.lang, label_obj.get("en", key))
            else:
                label_text = label_obj or key

        if field.get("required"):
            label_text += " *"
        return label_text

    def _create_input_widget(self, field, initial_data, index):
        """
        根据字段类型创建对应的输入控件。
        """
        field_type = field.get("type")
        readonly = field.get("readonly", False)
        key = field.get("key")

        if field_type == "combobox":
            widget = NoWheelComboBox()
            widget.setFont(self.base_font)
            widget.setStyleSheet(UIService.get_style("input_field"))
            widget.setFixedHeight(35)
            self._load_combobox_options(widget, field)

            val = ""
            if initial_data is not None:
                val = str(initial_data[index] if index is not None else "")

            # 如果没有初值或初值为空，尝试使用默认值
            if not val:
                val = str(field.get("default", ""))

            if val:
                idx = widget.findData(val)
                if idx != -1:
                    widget.setCurrentIndex(idx)
                else:
                    widget.setCurrentText(val)

            if readonly: widget.setEnabled(False)

            # 如果是动作类型字段，绑定切换事件实现动态显隐
            if key == "action":
                widget.currentIndexChanged.connect(lambda _, w=widget: self.update_fields_visibility(w.currentData()))

        elif field_type == "text":
            widget = QTextEdit()
            widget.setFont(self.base_font)
            rows = field.get("rows", 3)
            widget.setFixedHeight(rows * 30)

            val = ""
            if initial_data is not None:
                val = str(initial_data[index] if index is not None else "")

            if not val:
                val = str(field.get("default", ""))

            if val: widget.setPlainText(val)
            if readonly: widget.setReadOnly(True)

        elif field.get("data_type") == "int":
            widget = NoWheelSpinBox()
            widget.setFont(self.base_font)
            widget.setStyleSheet(UIService.get_style("input_field"))
            widget.setFixedHeight(35)
            widget.setRange(field.get("min", 0), field.get("max", 999999))

            val_int = field.get("default", 0)
            if initial_data is not None:
                try:
                    val_int = int(initial_data[index] if index is not None else val_int)
                except:
                    pass

            widget.setValue(val_int)
            if readonly: widget.setEnabled(False)

        else:
            widget = QLineEdit()
            widget.setFont(self.base_font)
            widget.setStyleSheet(UIService.get_style("input_field"))
            widget.setFixedHeight(35)

            val = ""
            if initial_data is not None:
                val = str(initial_data[index] if index is not None else "")

            if not val:
                val = str(field.get("default", ""))

            if val: widget.setText(val)
            if readonly: widget.setReadOnly(True)

        return widget

    def _load_combobox_options(self, widget, field):
        """
        从配置源加载下拉框选项。
        """
        source = field.get("options_source")
        if not source:
            return

        source_path = os.path.join("config", source)
        source_data = FileService.load_json(source_path)

        # 处理不同格式的数据源
        if isinstance(source_data, list):
            for item in source_data:
                widget.addItem(str(item), str(item))
        elif isinstance(source_data, dict):
            # 兼容 actions.json 等结构
            for section_list in source_data.values():
                if not isinstance(section_list, list): continue
                for item in section_list:
                    if not isinstance(item, dict): continue

                    opt_key = item.get("key")
                    i18n_key = item.get("i18n_key")

                    if i18n_key:
                        label_text = self.t(i18n_key)
                    else:
                        label_obj = item.get("label", {})
                        if isinstance(label_obj, dict):
                            label_text = label_obj.get(self.lang, label_obj.get("en", opt_key))
                        else:
                            label_text = label_obj or opt_key

                    display_label = f"{opt_key} - {label_text}"
                    widget.addItem(display_label, opt_key)

                    # 存储该动作需要的字段
                    fields_str = item.get("fields", "")
                    if fields_str:
                        self.actions_config[opt_key] = [f.strip() for f in fields_str.split(",")]
                    else:
                        self.actions_config[opt_key] = []

    def update_fields_visibility(self, action_key):
        """
        根据所选动作动态更新字段的显示/隐藏。
        """
        if not self.actions_config:
            return

        visible_fields = self.actions_config.get(action_key, [])
        # 基础字段始终显示
        base_fields = ["id", "name", "action", "description", "wait", "timeout"]

        for key, (label, widget, row_idx) in self.field_rows.items():
            should_show = key in base_fields or key in visible_fields
            label.setVisible(should_show)
            widget.setVisible(should_show)

            # 强制调整 SizePolicy 以确保完全收缩空间
            if should_show:
                widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
                label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
            else:
                widget.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
                label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)

            # 使用 setRowVisible (PyQt 5.8+)
            if hasattr(self.form_layout, "setRowVisible"):
                self.form_layout.setRowVisible(row_idx, should_show)

    def get_data(self):
        """
        从所有输入控件中收集数据并返回列表形式。
        """
        data = []
        for field in self.fields:
            key = field.get("key")
            widget = self.inputs.get(key)
            if not widget:
                data.append("")
                continue

            if isinstance(widget, QComboBox):
                val = widget.currentData()
                if val is None: val = widget.currentText()
                data.append(val)
            elif isinstance(widget, QSpinBox):
                data.append(widget.value())
            elif isinstance(widget, QTextEdit):
                data.append(widget.toPlainText())
            else:
                data.append(widget.text())
        return data


class BaseDataTable(QTableWidget):
    """
    数据表格基类，封装了通用的表格操作，如复制、粘贴、移动行和上下文菜单。
    """

    def __init__(self, t):
        super().__init__()
        self.t = t

        # 初始化基础字体
        font_settings = UIService.get_font_settings()
        self.base_font = QFont(font_settings.get("font_family", "Sans Serif"), font_settings.get("font_size", 12))
        self.setFont(self.base_font)

        # 应用样式
        self.setStyleSheet(UIService.get_style("table"))

        # 设置表格通用属性
        self._init_base_properties()

    def _init_base_properties(self):
        """
        初始化表格的基本显示和交互属性。
        """
        self.horizontalHeader().setFont(self.base_font)
        self.verticalHeader().setFont(self.base_font)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        # 默认禁用拖拽移动
        self._set_drag_enabled(False)

    def _set_drag_enabled(self, enabled):
        """
        设置是否允许通过拖拽移动行。
        """
        if enabled:
            self.setDragEnabled(True)
            self.setAcceptDrops(True)
            self.setDragDropMode(QTableWidget.InternalMove)
            self.setDropIndicatorShown(True)
            self.setSelectionMode(QTableWidget.ExtendedSelection)
        else:
            self.setDragEnabled(False)
            self.setAcceptDrops(False)
            self.setDragDropMode(QTableWidget.NoDragDrop)
            self.setSelectionMode(QTableWidget.ExtendedSelection)

    def dropEvent(self, event):
        """
        参考用户提供的稳定版逻辑，实现 100% 数据完整的“行整体插入”移动。
        采用“数据快照 -> 逻辑移动 -> 界面重绘”的稳定方案。
        """
        if event.source() != self:
            event.ignore()
            return

        # 1. 阻止 Qt 的默认物理移动，我们手动接管
        event.setDropAction(Qt.IgnoreAction)

        # 2. 获取选中的行索引 (确保去重并排序)
        selected_rows = sorted(list(set(idx.row() for idx in self.selectedIndexes())))
        if not selected_rows:
            return

        # 3. 计算目标落点行
        dst_row = self.rowAt(event.pos().y())
        if dst_row == -1:
            dst_row = self.rowCount()

        # 4. 计算向下拖拽时的偏移修正
        # 如果目标位置在选中行之后，插入点需要减去这些行本身占据的位置
        offset = sum(1 for r in selected_rows if r < dst_row)
        dst_row -= offset

        # 5. 提取全表数据快照
        full_data_snapshot = []
        for r in range(self.rowCount()):
            row_data = []
            for c in range(self.columnCount()):
                item = self.item(r, c)
                row_data.append(item.text() if item else "")
            full_data_snapshot.append(row_data)

        # 6. 从快照中提取选中的数据行
        moving_rows_data = [full_data_snapshot[r] for r in selected_rows]

        # 7. 从原快照中删除这些行 (必须倒序删除，防止索引错乱)
        for r in reversed(selected_rows):
            full_data_snapshot.pop(r)

        # 8. 在目标位置插入这些行
        for i, row in enumerate(moving_rows_data):
            full_data_snapshot.insert(dst_row + i, row)

        # 9. 刷新同步到 UI 界面
        self.blockSignals(True)
        self.setUpdatesEnabled(False)
        try:
            self.setRowCount(0)
            self.setRowCount(len(full_data_snapshot))
            for r, row_data in enumerate(full_data_snapshot):
                for c, val in enumerate(row_data):
                    new_item = QTableWidgetItem(str(val))
                    self.setItem(r, c, new_item)

            # 10. 恢复选中状态
            self.clearSelection()
            for i in range(len(moving_rows_data)):
                self.selectRow(dst_row + i)
        finally:
            self.setUpdatesEnabled(True)
            self.blockSignals(False)

        # 11. 触发数据结构改变钩子 (例如更新序号)
        self.on_data_structure_changed()
        event.accept()

    def show_context_menu(self, pos):
        """
        显示通用的右键菜单（复制、粘贴、上移、下移）。
        """
        menu = QMenu()
        menu.setFont(self.base_font)

        copy_act = menu.addAction(self.t("copy_row"))
        paste_act = menu.addAction(self.t("paste_row"))
        menu.addSeparator()
        up_act = menu.addAction(self.t("move_up"))
        down_act = menu.addAction(self.t("move_down"))

        action = menu.exec_(self.mapToGlobal(pos))
        if action == copy_act:
            self.copy_rows()
        elif action == paste_act:
            self.paste_rows()
        elif action == up_act:
            self.move_row(-1)
        elif action == down_act:
            self.move_row(1)

    def copy_rows(self):
        """
        将选中行的数据复制到剪贴板，存储为 JSON 字符串。
        """
        import json
        selected_ranges = self.selectedRanges()
        if not selected_ranges: return

        rows_data = []
        for r in selected_ranges:
            for row in range(r.topRow(), r.bottomRow() + 1):
                row_data = [self.item(row, col).text() if self.item(row, col) else ""
                            for col in range(self.columnCount())]
                rows_data.append(row_data)

        QApplication.clipboard().setText(json.dumps(rows_data))

    def paste_rows(self):
        """
        从剪贴板读取数据并插入到当前行之后。
        """
        import json
        try:
            data_str = QApplication.clipboard().text()
            rows_data = json.loads(data_str)
            if not isinstance(rows_data, list): return

            current_row = self.currentRow()
            target_row = current_row + 1 if current_row != -1 else self.rowCount()

            for row_data in rows_data:
                self.insertRow(target_row)
                for col, val in enumerate(row_data):
                    if col < self.columnCount():
                        self.setItem(target_row, col, QTableWidgetItem(str(val)))
                target_row += 1

            self.on_data_structure_changed()
        except:
            pass

    def move_row(self, delta):
        """
        将当前选中的行向上或向下移动。
        """
        row = self.currentRow()
        if row == -1: return

        new_row = row + delta
        if 0 <= new_row < self.rowCount():
            for col in range(self.columnCount()):
                item1 = self.takeItem(row, col)
                item2 = self.takeItem(new_row, col)
                self.setItem(row, col, item2)
                self.setItem(new_row, col, item1)

            self.setCurrentCell(new_row, 0)
            self.on_data_structure_changed()

    def on_data_structure_changed(self):
        """
        数据结构改变后的钩子方法（如更新行号），子类可重写。
        """
        pass


class ExcelTable(BaseDataTable):
    """
    Excel 数据展示表格，继承自 BaseDataTable。
    针对抓取步骤的字段配置进行了优化。
    """

    def __init__(self, fields, t, lang="zh"):
        super().__init__(t)
        self.fields = fields
        self.lang = lang

        self._setup_headers()
        # 初始化列宽
        for i, field in enumerate(self.fields):
            self.setColumnWidth(i, field.get("width", 100))

    def _setup_headers(self):
        """
        根据字段配置初始化国际化表头。
        """
        self.setColumnCount(len(self.fields))
        headers = []
        for f in self.fields:
            i18n_key = f.get("i18n_key")
            if i18n_key:
                headers.append(self.t(i18n_key))
            else:
                label_obj = f.get("label", {})
                if isinstance(label_obj, dict):
                    headers.append(label_obj.get(self.lang, label_obj.get("en", f.get("key"))))
                else:
                    headers.append(label_obj or f.get("key"))
        self.setHorizontalHeaderLabels(headers)

    def on_data_structure_changed(self):
        """
        重写钩子，在粘贴或移动后更新序号列。
        """
        for row in range(self.rowCount()):
            self.setItem(row, 0, QTableWidgetItem(str(row + 1)))


class JsonTable(BaseDataTable):
    """
    JSON 数据预览与编辑表格，继承自 BaseDataTable。
    支持直接加载和导出列表字典结构。
    """

    def __init__(self, data_list, t):
        super().__init__(t)
        self.data_list = data_list
        self.headers = list(data_list[0].keys()) if data_list else []

        self._setup_headers()
        self.load_data()

    def _setup_headers(self):
        """
        初始化表头，并尝试进行字段翻译。
        """
        self.setColumnCount(len(self.headers))
        translated_headers = []
        for h in self.headers:
            key = f"field_{h}"
            translated = self.t(key)
            translated_headers.append(translated if translated != key else h)
        self.setHorizontalHeaderLabels(translated_headers)

    def load_data(self):
        """
        将列表字典数据加载到表格中。
        """
        self.setRowCount(len(self.data_list))
        for r, item in enumerate(self.data_list):
            for c, key in enumerate(self.headers):
                val = item.get(key, "")
                self.setItem(r, c, QTableWidgetItem(str(val)))

    def get_data(self):
        """
        将表格当前内容读回并转换为列表字典。
        """
        new_list = []
        for r in range(self.rowCount()):
            item = {}
            for c, key in enumerate(self.headers):
                table_item = self.item(r, c)
                item[key] = table_item.text() if table_item else ""
            new_list.append(item)
        return new_list
