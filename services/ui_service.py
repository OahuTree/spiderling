import os
import platform
from services.file_service import FileService


class UIService:
    """
    UI 配置服务类，负责加载 settings.json 并在程序中提供跨平台的字体和样式设置。
    """
    _config = None
    _current_platform = platform.system()
    
    @classmethod
    def get_config(cls):
        if cls._config is None:
            config_path = os.path.join("config", "settings.json")
            cls._config = FileService.load_json(config_path)
            
            # 如果加载失败或文件不存在，提供基本的硬编码默认值
            if not cls._config:
                cls._config = {
                    "version": "1.0.0",
                    "ui": {
                        "Windows": {
                            "font_family": "Segoe UI",
                            "font_size": 12,
                            "mono_family": "Consolas",
                            "mono_size": 11,
                            "styles": {}
                        },
                        "Darwin": {
                            "font_family": ".AppleSystemUIFont",
                            "font_size": 14,
                            "mono_family": "Menlo",
                            "mono_size": 13,
                            "styles": {}
                        },
                        "Linux": {
                            "font_family": "Sans Serif",
                            "font_size": 12,
                            "mono_family": "Monospace",
                            "mono_size": 11,
                            "styles": {}
                        }
                    }
                }
        return cls._config

    @classmethod
    def get_version(cls):
        return cls.get_config().get("version", "1.0.0")

    @classmethod
    def get_style(cls, key, default=""):
        config = cls.get_config()
        platform_settings = config.get("ui", {}).get(cls._current_platform, {})
        return platform_settings.get("styles", {}).get(key, default)

    @classmethod
    def get_font_settings(cls):
        config = cls.get_config()
        return config.get("ui", {}).get(cls._current_platform, {
            "font_family": "Sans Serif",
            "font_size": 12,
            "mono_family": "Monospace",
            "mono_size": 11
        })

    @classmethod
    def t(cls, key, lang="zh-CN"):
        """翻译多语言版本"""
        try:
            locales_path = os.path.join("config", "locales", f"{lang}.json")
            data = FileService.load_json(locales_path, default_data={})
            return data.get(key, key)
        except:
            return key
