import os
import re
import pandas as pd
from services.file_service import FileService


class DataStageService:
    """
    数据转换服务类，根据 stage_type.json 中的配置对 DataFrame 进行批量转换。
    """

    @staticmethod
    def transform(df, stage_key):
        """
        根据给定的 key，从配置文件加载规则并应用到 DataFrame。
        """
        if df is None or df.empty or not stage_key:
            return df

        # 获取当前文件所在目录的上一级，然后进入 config
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        config_path = os.path.join(base_dir, "config", "stage_type.json")
        
        rules_data = FileService.load_json(config_path, default_data={"stage": []})
        rules = rules_data.get("stage", [])

        # 查找匹配的规则
        rule = next((r for r in rules if r.get("key") == stage_key), None)
        if not rule:
            # 如果没找到规则，直接返回原数据
            return df

        pattern = rule.get("pattern")
        action = rule.get("action")

        if not pattern or not action:
            return df

        # 构建元素级转换函数
        def _apply_convert(val):
            if val is None or pd.isna(val):
                return val
            
            # 转为字符串执行正则判断
            # 如果是浮点数且可能是大整数，尝试转为非科学计数法字符串
            if isinstance(val, (float, int)) and abs(val) >= 1e14:
                s_val = "{:.0f}".format(val)
            else:
                s_val = str(val).strip()

            if re.match(pattern, s_val):
                try:
                    if action == "str":
                        return s_val
                    elif action == "float":
                        # 处理可能的百分比符号
                        clean_num = re.sub(r'[^\d\.\-\%]', '', s_val)
                        if '%' in clean_num:
                            return float(clean_num.replace('%', '')) / 100.0
                        return float(clean_num)
                    elif action == "int":
                        # 尝试提取数字部分
                        clean_num = re.sub(r'[^\d\-]', '', s_val)
                        return int(float(clean_num))
                except Exception:
                    # 转换失败则保持原样
                    return val
            return val

        # 使用 map (新版 pandas) 或 applymap (旧版) 对 DataFrame 的每个单元格应用转换逻辑
        if hasattr(df, 'map'):
            return df.map(_apply_convert)
        return df.applymap(_apply_convert)
