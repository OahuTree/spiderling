import ctypes
import sys
import json
import os
import traceback
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QListWidget, QTabWidget, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem, QCheckBox,
                             QMessageBox, QDockWidget, QTextEdit)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QTextCursor, QIcon, QPixmap
from services.file_service import FileService
from services.scrape_service import ScrapeService
from services.ui_service import UIService


def exception_hook(exctype, value, tb):
    """
    全局异常捕获钩子，防止程序因未捕获异常而直接退出。
    将错误信息格式化后通过消息框展示给用户。
    """
    error_msg = "".join(traceback.format_exception(exctype, value, tb))
    print(error_msg)  # 控制台打印，方便调试
    # 弹出错误对话框
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Critical)
    msg.setWindowTitle(UIService.t("sys_error"))
    msg.setText(UIService.t("sys_error_tip"))
    msg.setInformativeText(str(value))
    msg.setDetailedText(error_msg)
    msg.setStandardButtons(QMessageBox.Ok)
    msg.exec_()
    sys.exit(1)


# 设置系统异常钩子
sys.excepthook = exception_hook


class MainWindow(QMainWindow):
    """
    主窗口类，负责程序的整体框架、菜单栏管理及多文档界面（MDI）逻辑。
    """

    def __init__(self):
        """
        初始化主窗口，设置标题、尺寸并加载配置。
        """
        super().__init__()

        # 加载语言配置
        self.languages = self.load_languages()

        # 从配置文件加载上次保存的语言，默认 zh-CN
        self.settings_path = os.path.join("config", "settings.ini")
        settings = FileService.load_ini(self.settings_path)
        self.current_lang = settings.get("General", {}).get("language", "zh-CN")

        # 确保加载的语言在支持列表中，否则回退到默认
        if not any(l["code"] == self.current_lang for l in self.languages):
            self.current_lang = "zh-CN"

        self.i18n_data = self.load_i18n(self.current_lang)

        self.setWindowTitle(self.t("app_title"))
        self.resize(1920, 1080)

        # 设置窗口图标
        icon_path = os.path.join("assets", "logo.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # 获取版本号
        self.version = UIService.get_version()

        # 加载菜单配置文件
        self.menu_config = self.load_config()

        # 初始化用户界面
        self.setup_ui()

        # 启动时自动打开工作台
        self.open_tab({"id": "open", "label": "打开工作台", "i18n_key": "open_workspace", "component": "Dashboard"})
        if self.tabs.count() > 0:
            self.tabs.setCurrentIndex(0)

        # 初始化日志输出
        self.add_log(self.t("system_ready"), "blue")

    def setup_corner_widget(self):
        """配置标签栏右侧的品牌角落部件"""
        corner_widget = QWidget()
        corner_layout = QHBoxLayout(corner_widget)
        corner_layout.setContentsMargins(10, 0, 15, 0)
        corner_layout.setSpacing(8)

        # Logo
        logo_label = QLabel()
        logo_path = os.path.join("assets", "logo.png")
        if os.path.exists(logo_path):
            logo_pixmap = QPixmap(logo_path).scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(logo_pixmap)

        # 品牌
        brand_label = QLabel("Spiderling")
        brand_label.setStyleSheet(
            f"font-weight: bold; font-family: {UIService.get_font_settings().get('font_family')}; color: #1d1d1f;")

        # 版本
        version_label = QLabel(f"v{self.version}")
        version_label.setStyleSheet("color: #86868b; font-size: 11px;")

        corner_layout.addWidget(logo_label)
        corner_layout.addWidget(brand_label)
        corner_layout.addWidget(version_label)

        self.tabs.setCornerWidget(corner_widget, Qt.TopRightCorner)

    def add_log(self, msg, color="black"):
        """
        向全局日志区域添加一条记录。
        支持简单的 HTML 颜色渲染。
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        mono_font = UIService.get_font_settings().get("mono_family", "Consolas")
        # 组装带时间戳的信息
        html_msg = f"<div style='margin-bottom: 4px;'>" \
                   f"<span style='color: #888888; font-family: {mono_font};'>[{timestamp}]</span> " \
                   f"<span style='color: {color}; font-weight: 500;'>{msg}</span>" \
                   f"</div>"

        self.log_output.append(html_msg)
        # 自动滚动到底部
        self.log_output.moveCursor(QTextCursor.End)

    def clear_logs(self):
        """清空日志记录"""
        self.log_output.clear()
        self.add_log(self.t("system_ready"), "blue")

    def load_languages(self):
        """加载支持的语言列表"""
        path = os.path.join("config", "languages.json")
        return FileService.load_json(path, default_data=[{"code": "zh", "label": "中文"}])

    def load_i18n(self, lang):
        """加载指定语言的国际化配置"""
        path = os.path.join("config", "locales", f"{lang}.json")
        return FileService.load_json(path, default_data={})

    def t(self, key):
        """翻译函数"""
        return self.i18n_data.get(key, key)

    def change_language(self, lang_code):
        """切换语言"""
        self.current_lang = lang_code
        self.i18n_data = self.load_i18n(lang_code)
        # 重新创建菜单栏以刷新翻译
        self.menuBar().clear()
        self.create_menu_bar()
        # 标签页内容这里没有进行刷新，标签页将在下次启动后切换语言。
        QMessageBox.information(self, self.t("success"), self.t(
            "lang_changed_tip") if "lang_changed_tip" in self.i18n_data else "Language changed. Please restart or refresh tabs if needed.")

    def load_config(self):
        """
        从 JSON 文件加载菜单配置。

        Returns:
            dict: 包含菜单层级结构的字典。如果文件不存在，返回包含空菜单的默认字典。
        """
        config_path = os.path.join("config", "menu.json")
        return FileService.load_json(config_path, default_data={"menu": []})

    def setup_ui(self):
        """
        构建主窗口的 UI 布局，包括菜单栏、标签页工作区和状态栏。
        """
        # 设置中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 创建顶部菜单栏
        self.create_menu_bar()

        # 创建主工作区（标签页控件）
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)  # 允许关闭标签页
        self.tabs.setMovable(True)  # 允许拖动标签页
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.setStyleSheet(UIService.get_style("tab_widget"))

        # 强制设置标签栏属性
        self.tabs.setTabBarAutoHide(False)
        self.tabs.setDocumentMode(False)  # 关闭文档模式以确保左对齐生效
        self.tabs.tabBar().setExpanding(False)  # 标签宽度自适应内容
        self.tabs.tabBar().setProperty("alignment", Qt.AlignLeft)  # 强制设置对齐属性
        self.tabs.tabBar().setMovable(True)

        # 创建顶部角落部件（Logo, 品牌, 版本号）
        self.setup_corner_widget()

        main_layout.addWidget(self.tabs)

        # 创建底部状态栏
        self.status = self.statusBar()
        self.status.showMessage(self.t("status_ready"))
        self.status.setStyleSheet(
            "font-size: 13px; color: #86868b; background: #f8f9fa; border-top: 1px solid #e0e0e0; padding: 3px;")

        # 创建全局日志区域 (DockWidget)
        self.log_dock = QDockWidget(self.t("log_center") if "log_center" in self.i18n_data else "操作日志", self)
        self.log_dock.setAllowedAreas(Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)

        font_settings = UIService.get_font_settings()
        self.log_output.setFont(QFont(font_settings.get("mono_family"), font_settings.get("mono_size")))
        self.log_output.setStyleSheet(UIService.get_style("log_area"))

        self.log_dock.setWidget(self.log_output)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.log_dock)

    def create_menu_bar(self):
        """
        根据加载的配置动态创建顶部菜单栏及其下拉项。
        """
        menu_bar = self.menuBar()
        menu_bar.clear()  # 清空旧菜单
        menu_bar.setStyleSheet(UIService.get_style("menu_bar"))

        # 遍历配置中的菜单分类
        for category in self.menu_config.get("menu", []):
            label = self.t(category.get("i18n_key", category["label"]))
            menu = menu_bar.addMenu(label)
            # 遍历分类下的具体菜单项
            for item in category.get("items", []):
                item_label = self.t(item.get("i18n_key", item["label"]))
                action = menu.addAction(item_label)
                # 绑定点击事件
                if item["id"] == "exit":
                    action.triggered.connect(self.close)
                elif item["id"] == "about":
                    action.triggered.connect(self.show_about_dialog)
                else:
                    action.triggered.connect(lambda checked, i=item: self.open_tab(i))

        # 添加语言切换菜单
        # lang_menu = menu_bar.addMenu(self.t("menu_language"))
        lang_menu = menu_bar.addMenu("Language")
        for lang in self.languages:
            action = lang_menu.addAction(lang["label"])
            action.triggered.connect(lambda checked, code=lang["code"]: self.change_language(code))

    def show_about_dialog(self):
        """显示关于对话框及 Logo"""
        msg = QMessageBox(self)
        msg.setWindowTitle(self.t("about"))

        logo_path = os.path.join("assets", "logo.png")
        if os.path.exists(logo_path):
            from PyQt5.QtGui import QPixmap
            pixmap = QPixmap(logo_path).scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            msg.setIconPixmap(pixmap)

        msg.setText("Spiderling - Web Scraper")
        info_text = f"Version: v{self.version}\n\n" \
                    "A simple and efficient automated web scraping tool.\n\n" \
                    "GitHub: https://github.com/OahuTree/spiderling"
        msg.setInformativeText(info_text)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    def change_language(self, lang_code):
        """
        切换应用程序的显示语言，并保存到配置文件中。
        """
        try:
            self.current_lang = lang_code
            self.i18n_data = self.load_i18n(lang_code)

            # 保存到配置文件
            settings = FileService.load_ini(self.settings_path)
            if "General" not in settings:
                settings["General"] = {}
            settings["General"]["language"] = lang_code
            FileService.save_ini(self.settings_path, settings)

            # 重新创建菜单栏以刷新翻译文本
            self.create_menu_bar()
            # 标签页内容这里没有进行刷新，标签页将在下次启动后切换语言。
            self.status.showMessage(self.t("ready"))
            QMessageBox.information(self, self.t("success"), self.t("lang_changed_tip"))
        except Exception as e:
            # 捕获切换语言时的异常
            QMessageBox.warning(self, "Language Switch Error", str(e))

    def open_tab(self, item):
        """
        打开一个新的标签页或切换到已存在的标签页。
        如果标签页对应的组件加载失败，会弹出具体的错误信息。

        Args:
            item (dict): 包含标签页信息的字典，需包含 'label' 和 'component' 键。
        """
        try:
            label = self.t(item.get("i18n_key", item["label"]))

            # 检查同名标签页是否已存在
            for i in range(self.tabs.count()):
                if self.tabs.tabText(i) == label:
                    self.tabs.setCurrentIndex(i)
                    return

            # 创建容器部件及其布局
            new_tab = QWidget()
            layout = QVBoxLayout(new_tab)
            layout.setContentsMargins(20, 20, 20, 20)

            # 调用子窗体工厂生成具体功能界面
            self.create_child_window(new_tab, layout, item["component"])

            # 将新创建的业务视图加入标签页管理器
            idx = self.tabs.addTab(new_tab, label)
            self.tabs.setCurrentIndex(idx)

            # 记录打开操作
            self.add_log(f"{self.t('open_tab')}: {label}", "green")

        except Exception as e:
            # 记录并弹出加载失败的详细信息
            error_trace = traceback.format_exc()
            print(f"Tab creation failed: {e}\n{error_trace}")
            QMessageBox.critical(self, self.t("load_failed"),
                                 f"{self.t('cannot_create_tab')} '{item.get('label')}':\n{str(e)}")

    def close_tab(self, index):
        """
        关闭特定位置的标签页，并触发组件的清理逻辑。
        """
        widget = self.tabs.widget(index)
        if hasattr(widget, "cleanup"):
            try:
                widget.cleanup()
            except Exception as e:
                print(f"Cleanup error: {e}")
        self.tabs.removeTab(index)

    def closeEvent(self, event):
        """
        主窗口关闭事件，确保所有后台线程和资源被正确释放。
        """
        try:
            # 停止所有抓取服务中的线程
            ScrapeService.stop_all()
        except Exception as e:
            print(f"Error during stop_all: {e}")
        event.accept()

    def create_child_window(self, parent, layout, component_name):
        """
        工厂模式：根据配置中指定的组件名称动态导入并创建 UI。

        Args:
            parent (QWidget): 标签页的主容器部件。
            layout (QVBoxLayout): 容器的布局管理器。
            component_name (str): 逻辑组件标识符。
        """
        try:
            if component_name == "Dashboard":
                from ui import dashboard_view
                dashboard_view.create_dashboard(parent, layout, self.t, log_func=self.add_log,
                                                clear_log_func=self.clear_logs, lang=self.current_lang)
            elif component_name == "DataView":
                from ui import dataview_view
                dataview_view.create_dataview(parent, layout, self.t)
            elif component_name == "Settings":
                from ui import settings_view
                settings_view.create_settings(parent, layout, self.t)
            elif component_name == "JsonEditor":
                from ui import json_editor_view
                json_editor_view.create_json_editor(parent, layout, self.t, log_func=self.add_log)
            else:
                layout.addWidget(QLabel(f"{self.t('unknown_component')}: {component_name}"))
        except ImportError as ie:
            raise ImportError(f"{self.t('cannot_import_module')} '{component_name}': {ie}")
        except Exception as ex:
            raise RuntimeError(f"{self.t('init_error')} '{component_name}': {ex}")


if __name__ == "__main__":
    # 程序启动入口
    app = QApplication(sys.argv)

    # 在 macOS 上强制使用 Fusion 样式，以解决原生主题强制标签居中的问题
    import platform

    if platform.system().lower() == "darwin":
        app.setStyle("Fusion")

    if platform.system().lower() == "windows":
        # 加载程序图标。
        myappid = 'my_unique_app_id_string'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        icon_path = os.path.join("assets", "logo.png")
    elif platform.system().lower() == "darwin":
        icon_path = os.path.join("assets", "logo.icns")

    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
