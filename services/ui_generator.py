from PyQt5.QtWidgets import (QPushButton, QLabel, QLineEdit, QComboBox, 
                             QMessageBox, QStyle)
from PyQt5.QtGui import QFont, QIcon, QColor, QPixmap, QPainter
from PyQt5.QtCore import Qt
from services.ui_service import UIService

class UIGenerator:
    """
    UI 生成器类，提供统一的界面组件创建和样式设置工具方法。
    """
    @staticmethod
    def get_fonts():
        """
        获取系统预设的各类字体。
        返回: (基础字体, 标题字体, 按钮字体, 等宽字体)
        """
        font_settings = UIService.get_font_settings()
        base_font = QFont(font_settings.get("font_family"), font_settings.get("font_size"))
        title_font = QFont(font_settings.get("font_family"), font_settings.get("title_font_size"), QFont.Bold)
        btn_font = QFont(font_settings.get("font_family"), font_settings.get("btn_font_size"))
        mono_font = QFont(font_settings.get("mono_family"), font_settings.get("mono_size"))
        return base_font, title_font, btn_font, mono_font

    @staticmethod
    def setup_button(btn, font, style_key="button", color=None):
        """
        统一设置按钮的样式和字体。
        """
        style = UIService.get_style(style_key)
        if color:
            style = style.replace("color: #1d1d1f;", f"color: {color};")
        btn.setStyleSheet(style)
        btn.setFont(font)
        return btn

    @staticmethod
    def setup_input(widget, font, width=None):
        """
        统一设置输入框/下拉框的样式和字体。
        """
        widget.setFont(font)
        widget.setStyleSheet(UIService.get_style("input_field"))
        if width:
            widget.setFixedWidth(width)
        return widget

    @staticmethod
    def get_colored_icon(parent, standard_icon, color_str):
        """
        生成带有特定颜色的标准图标。
        """
        pixmap = parent.style().standardIcon(standard_icon).pixmap(24, 24)
        painter = QPainter(pixmap)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), QColor(color_str))
        painter.end()
        return QIcon(pixmap)

    @staticmethod
    def handle_exception(parent, t, e, log_func=None, prefix=""):
        """
        统一处理异常：弹出错误对话框并记录日志。
        """
        msg = f"{prefix}: {str(e)}"
        if log_func:
            log_func(msg, "red")
        QMessageBox.critical(parent, t("error") if "error" in t("error") else "Error", msg)
