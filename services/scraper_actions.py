import ast
import os
import re
import time
from io import StringIO

import pandas as pd
from urllib.parse import urlparse, parse_qs

from bs4 import BeautifulSoup
from selenium.common import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC

from services.db_service import DBService
from services.file_service import FileService


class ScraperActions:
    """
    具体的抓取动作实现类。
    """
    def __init__(self, driver, log_func=None, t=None, stop_event=None):
        self.driver = driver
        self.log_func = log_func
        self.t = t
        self.stop_event = stop_event

        # 下一个步骤， -1为忽略该值
        self.next_id = -1
        # current_record用于记录循环记录数
        self.current_record = 0
        # 定义缓存目录
        self.cache_path = self._get_cache_path()


    def _get_cache_path(self):
        """获取缓存目录"""
        _chrome_option_path = FileService.get_browser_user_data_dir()
        if not _chrome_option_path:
            _msg = "browser user path can not found.please config browser config."
            self.log(_msg, "red")
            raise RuntimeError(_msg)

        _cache_path = os.path.expanduser(_chrome_option_path) + ".cache"
        # 如果不存在缓存目录则创建一个
        if not os.path.exists(_cache_path):
            os.makedirs(_cache_path)

        return _cache_path


    def log(self, msg, color="black"):
        if self.log_func:
            self.log_func(msg, color)

    def navigate(self, row):
        """跳转 URL"""
        _url = row.get("url")
        _cache = row.get("cache")
        #
        if _cache:
            _urls = self._generate_urls(df=FileService.read_cache(config_path=self.cache_path, file_name=_cache, data_type="dataframe"), url_template=_url)
            _url = _urls[0]

        self._navigate(url=_url)

    def click(self, row):
        """点击元素"""
        _selector = row.get("selector")
        _script = row.get("script")
        self.log(f"{self.t('executing')}: click")
        if _script:
            # 通过javascript执行点击
            self._execute_js(_script, [])
            return

        if _selector:
            self.log(f"    {self.t('click_element')}: {_selector}")
            element = self.driver.find_element(By.CSS_SELECTOR, _selector)
            element.click()

    def input_text(self, row):
        """输入文本"""
        _selector = row.get("selector")
        _script = row.get("script")
        _input = row.get("input", "")
        _cache = row.get("cache")

        self.log(f"{self.t('executing')}: input_text")

        # 如果指定了 cache，则从缓存中读取内容作为输入
        if _cache:
            _content = FileService.read_cache(self.cache_path, _cache, data_type="string")
            if _content:
                _input = _content

        if _script:
            self.log(f"    {self.t('js_input')}: {_input}")
            self._execute_js(_script, [_input])
            return

        if _selector:
            self.log(f"    {self.t('input_text_to')}: {_selector} -> {_input}")
            _element = self.driver.find_element(By.CSS_SELECTOR, _selector)
            _element.clear()
            _element.send_keys(_input)

    def scrape_web(self, row):
        """抓取网页数据，将抓取到的网页碎片写入到variable参数指定的文件中"""
        _selector = row.get("selector")
        _attribute = row.get("attribute", "text")
        _variable = row.get("variable", "unknown")
        _script = row.get("script")
        # print(self.driver.current_url)
        self.log(f"{self.t('executing')}: scrape_web")
        if _script:
            # 如果script项不为空则使用javascript进行数据抓取。
            self.log(f" {_script}")
            _val = self._execute_js(_script, args=[])
            FileService.write_cache(config_path=self.cache_path, file_name=_variable, data=_val,
                                    delete_existing=True)
            self.log(f" {_val}")
            return

        if _selector:
            self.log(f"  {self.t('scrape_element')}: {_selector} ({_attribute}) -> {_variable}")
            _element = self.driver.find_element(By.CSS_SELECTOR, _selector)
            if _attribute == "text":
                _val = _element.text
            else:
                _val = _element.get_attribute(_attribute)

            FileService.write_cache(config_path=self.cache_path, file_name=_variable, data=_val, delete_existing=True)
            self.log(f"{self.t('scrape_result')}: {_val}")
            # 这里后续可以扩展存储逻辑
        else:
            self.log(self.t("err_no_selector"), "red")

    def parse_html(self, row):
        """解析 HTML，将解析的内容保存在cache指定的文件中"""
        # _selector = row.get("selector")
        # _attribute = row.get("attribute", "text")
        _source_type = row.get("source_type")
        _variable = row.get("variable", "unknown")
        # 读取本地缓存的html碎片
        _cache_source = FileService.read_cache(config_path=self.cache_path, file_name=row.get("cache"), data_type="string")

        self.log(f"{self.t('executing')}: parse_html {_source_type}")

        method_name = f"_parse_html_{_source_type}"
        method = getattr(self, method_name, None)

        _soup = BeautifulSoup(_cache_source, 'html.parser')
        if method:
            _df = method(row, _soup)
            # print(df)
            FileService.write_cache(config_path=self.cache_path, file_name=_variable, data=_df, delete_existing=False)
        else:
            raise ValueError(f"{self.t('err_unsupported_source')}: {_source_type}")

    def parse_url(self, row):
        """从 URL 中解析内容"""
        _variable = row.get("variable", "unknown")
        _selector = row.get("selector")
        _current_url = self.driver.current_url
        self.log(f"{self.t('executing')}: parse_url {_selector}")

        # 解析 URL
        _parsed_url = urlparse(_current_url)
        # 提取查询参数并转为字典
        _params = parse_qs(_parsed_url.query)

        _value = _params.get(_selector, [None])[0]

        _df = self._create_df(_selector, _value)
        # 保存到变量文件
        FileService.write_cache(config_path=self.cache_path, file_name=_variable, data=_df, delete_existing=False)

        self.log(f"{self.t('parse_result')}: {_value}")

    def delay(self, row):
        """延迟"""
        _wait_val = row.get("input", 0)
        try:
            _seconds = float(_wait_val)
            if _seconds > 0:
                self.log(f"{self.t('waiting_seconds')} {_seconds} s...")
                if self.stop_event:
                    self.stop_event.wait(_seconds)
                else:
                    time.sleep(_seconds)
        except:
            pass

    def iterate_file(self, row):
        """从cache，variable文件中读取数据，variable文件记录当前处理的行数,cache文件记录整个数据集"""
        _cache_file = row.get("cache")
        _variable_file = row.get("variable")
        _url = row.get("url")
        _current = FileService.read_cache(config_path=self.cache_path, file_name=_variable_file, data_type="int")

        if _current is None:
            _current = 0

        self.log(f"{self.t('executing')}: iterate_file {_current}")
        # 读取需要循环的数据，只能是dataframe类型。
        _data = FileService.read_cache(config_path=self.cache_path, file_name=_cache_file, data_type="dataframe")

        # _one_data = _data[self.current_record]

        if _url:
            # 生成新的一列 'full_url'
            _urls = self._generate_urls(df=_data, url_template=_url)
            # print(_urls)
            print(_urls[_current])
            self._navigate(_urls[_current])

        self.current_record = _current + 1
        FileService.write_cache(config_path=self.cache_path, file_name=_variable_file, data=self.current_record, delete_existing=True)

        self.next_id = -1

    def end_iteration(self, row):
        """结束iterate_file循环"""
        _cache_file = row.get("cache")
        _variable_file = row.get("variable")
        _current = FileService.read_cache(config_path=self.cache_path, file_name=_variable_file, data_type="int")

        # _data = FileService.read_cache(config_path=self.cache_path, file_name=_variable_file, data_type=row.get("source_type"))
        _data_len = FileService.get_cache_count(config_path=self.cache_path, file_name=_cache_file, data_type="dataframe")

        if _current < _data_len:
            # 继续循环
            self.next_id = int(row["input"]) - 1
        else:
            # 退出循环
            self.next_id = -1
            self.current_record = 0


        self.log(f"{self.t('executing')}:end_iteration {self.next_id}")

    def stage_data(self, row):
        """准备数据：对 DataFrame 进行格式转换"""
        _input_file = row.get("cache")
        _output_file = row.get("variable")
        _stage_key = row.get("stage_type")

        self.log(f"{self.t('executing')}: stage_data input={_input_file}, output={_output_file}, type={_stage_key}")

        if not _input_file:
            self.log(self.t("err_stage_no_cache"), "red")
            return

        try:
            # 1. 读取数据
            df = FileService.read_cache(self.cache_path, _input_file, data_type="dataframe")
            if df is None or df.empty:
                self.log(f"{self.t('warn_cache_empty')}: {_input_file}", "yellow")
                return

            # 2. 如果指定了 stage_type，则调用 DataStageService 进行转换
            if _stage_key:
                from services.data_stage_service import DataStageService
                df = DataStageService.transform(df, _stage_key)
                self.log(f"{self.t('applied_transform')}: {_stage_key}")

            # 3. 如果指定了输出变量，则保存结果
            if _output_file:
                FileService.write_cache(self.cache_path, _output_file, df, delete_existing=True)
                self.log(f"{self.t('data_processed_save')}: {_output_file}")
            else:
                self.log(self.t("warn_no_variable_stage"), "yellow")

        except Exception as e:
            self.log(f"{self.t('err_stage_data_exec')}: {str(e)}", "red")

    def clear_cache(self, row):
        """清除cache文件"""
        _file_name = row.get("cache")
        FileService.del_cache(config_path=self.cache_path, file_name=row.get("cache"))
        self.log(f"{self.t('executing')}: clear_cache {_file_name}")

    def commit_db(self, row):
        """将cache中的文件提交到数据表variable"""

        try:
            _table_name = row.get("variable")
            _cache_file = row.get("cache")

            self.log(f"{self.t('executing')}: commit_db {_cache_file}")
            if not _table_name:
                self.log(self.t("err_no_table_commit"), "red")
                return

            # 读取待提交的数据 (DataFrame)
            _df = FileService.read_cache(config_path=self.cache_path, file_name=_cache_file, data_type="dataframe")

            if _df is None or _df.empty:
                self.log(f"{self.t('warn_no_data_to_commit')}: {_cache_file}", "yellow")
                return

            # 处理大数字问题
            _df = self._format_large_integers(df=_df)
            # 执行保存
            success, msg = DBService.save_dataframe(_df, _table_name, if_exists='append')

            if success:
                self.log(f"{self.t('commit_success_rows')} [{_table_name}]: {_df.shape[0]}", "green")
            else:
                self.log(f"{self.t('commit_failed')}: {msg}", "red")

        except Exception as e:
            self.log(f"{self.t('err_commit_db_exec')}: {str(e)}", "red")

    def jump_to(self, row):
        """
            执行跳转
            执行跳转需要用的参数为:
                cache   跳转文件，用于存放当前的值
                variable    最高跳转次数，超过这个数值则结束跳转
                input   要跳转的步骤序号
        """
        try:
            self.log(f"{self.t('executing')}: jump_to")
            _current = FileService.read_cache(config_path=self.cache_path, file_name=row.get("cache"), data_type="int")
            _max = self._safe_int(row.get("variable"), 1)
            _next = self._safe_int(row.get("input"))
            if _max < _current:
                # 停止跳转
                self.next_id = -1
                self.log(f"{self.t('jump_max_reached')}: {_max} <= {_current}")
            else:
                self.next_id = _next - 1
                self.log(f"{self.t('jump_step_to')}: {_next} ({_current}/{_max})")

        except Exception as e:
            self.log(f"{self.t('err_jump_to_exec')}: {str(e)}", "red")

    def reset_flow(self, row):
        """
        还原jump_to的跳转点
            使用jump_to步骤后，必须返回的是reset_flow步骤，否则会一直循环。
            reset_flow函数的作用是结束跳转，使整个流程恢复正常。
        """
        self.log(f"{self.t('executing')}: reset_flow")
        self.next_id = -1

    def remap(self, row):
        """处理df列名转换"""
        _remap = row.get("remap")
        _df = FileService.read_cache(config_path=self.cache_path, file_name=row.get("cache"), data_type="dataframe")
        self.log(f"{self.t('executing')}: remap {_remap}")

        # 将字符串转换为字典
        _mapping_dict = ast.literal_eval(_remap)

        # 应用到 DataFrame
        _df.rename(columns=_mapping_dict, inplace=True)
        # 过滤
        # 提取 mapping_dict 中的所有新列名（Values）
        _target_db_columns = list(_mapping_dict.values())

        # 找出 DataFrame 中实际存在的、且在对照表（Values）里的列
        _valid_columns = _df.columns.intersection(_target_db_columns)

        # 过滤 DataFrame
        _df = _df[_valid_columns]

        # 转换大数字
        _df = self._format_large_integers(_df)

        FileService.write_cache(config_path=self.cache_path, file_name=row.get("variable"), data=_df, delete_existing=True)

    def _navigate(self, url):
        """跳转 URL"""
        if url:
            self.log(f"{self.t('action_navigate')}: {url}")
            self.driver.get(url)
            WebDriverWait(self.driver, 20)
            print(self.driver.title)
        else:
            self.log(self.t("err_no_url"), "red")

    def _create_df(self, key, value):
        """根据key, value 创建dataframe"""
        data = {
            key: value
        }
        return pd.DataFrame([data])

    def _execute_js(self, script, args):
        """运行javascript"""

        try:
            self.log(f"{self.t('exec_js')}: -> {args}")
            result = self.driver.execute_script(script, *args)

            return result
        except TimeoutException:
            self.log(self.t("err_selector_not_found"))

        except Exception as e:
            self.log(f"{self.t('err_scrape_control')}: {str(e)}")

    def _format_large_integers(self, df):
        """转换大数字为字符串"""
        for col in df.columns:
            if df[col].dtype == "uint64":
                df[col] = df[col].astype(str)
        return df

    def _generate_urls(self, df, url_template):
        """
        根据 URL 模板中的 {参数} 自动匹配 DataFrame 中的列并生成 URL 列表
        """
        # 1. 提取模板中所有花括号内的参数名
        needed_params = re.findall(r'\{(.*?)\}', url_template)

        if not needed_params:
            return [url_template] * len(df)

        # 2. 检查 DataFrame 是否包含所有需要的列
        missing_cols = [p for p in needed_params if p not in df.columns]
        if missing_cols:
            raise ValueError(f"DataFrame 中缺失以下列: {missing_cols}")

        # 3. 动态填充：遍历每一行，将行数据转为字典后填充到模板
        # 按行处理，row.to_dict() 会自动匹配模板中的同名键
        urls = df.apply(lambda row: url_template.format_map(row.to_dict()), axis=1).tolist()

        return urls

    def _parse_html_dataframe(self, row, _soup):
        """通过DIV配对块来读取数据"""
        _data = {}

        _labels = _soup.select(row.get("selector"))
        _values = _soup.select(row.get("attribute"))

        if _labels and _values and len(_labels) == len(_values):
            for _l, _v in zip(_labels, _values):
                _label = _l.get_text(strip=True)
                _value = _v.get_text(strip=True)
                _data[_label] = _value

        return pd.DataFrame([_data])

    def _parse_html_table(self, row, _soup):
        """读取table数据"""
        _selector = row.get("selector")
        table_html = _soup.select_one(_selector)
        _df = pd.read_html(StringIO(str(table_html)))[0]

        return _df

    def _parse_html_list(self, row, _soup):
        """读取选择相同名称控件中的属性值"""
        _rows = _soup.select(row.get("selector"))
        _vals = [r.get(row.get("attribute")) for r in _rows]
        _df = pd.DataFrame(_vals, columns=[row.get("attribute")])
        return _df

    def _parse_html_string(self, row, _soup):
        """根据css selector和attribute读取控件中的属性值"""
        _selector = row.get("selector")
        _attribute = row.get("attribute")
        _input = row.get("input")
        _element = _soup.select_one(_selector)
        if _attribute.lower() in ["text", "innertext"]:
            _val = _element.get_text(strip=True)
        else:
            _val = _element.get(_attribute, "")

        if _input:
            _df = self._create_df(_input, _val)
        else:
            _df = self._create_df(_attribute, _val)
        return _df

    def _safe_int(self, val, default=0):
        """安全地将值转换为整数"""
        # 1. 处理 None 和空字符串
        if val is None:
            return default

        s_val = str(val).strip().lower()
        if s_val in ("", "none", "null"):
            return default

        try:
            # 2. 先转 float 再转 int，能处理 "x.0"格式的浮点数
            return int(float(val))
        except (ValueError, TypeError):
            return default
