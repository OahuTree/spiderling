import os
import time
import json
import subprocess
import socket
import platform
import threading
import shutil
from PyQt5.QtCore import QObject, pyqtSignal
from psycopg2.errorcodes import RAISE_EXCEPTION
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from services.file_service import FileService


class ScrapeWorker(QObject):
    """
    抓取任务工作类。
    """
    finished_signal = pyqtSignal()
    log_signal = pyqtSignal(str, str)  # msg, color

    def __init__(self, t, config, data, sheet_name):
        super().__init__()
        self.t = t
        self.config = config
        self.data = data
        self.sheet_name = sheet_name
        self.stop_event = threading.Event() # 结束停止信号
        self.driver = None

    def log(self, msg, color="black"):
        self.log_signal.emit(msg, color)

    def is_running(self):
        return not self.stop_event.is_set()

    def is_port_open(self, host, port):
        # with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        #     s.settimeout(1)
        #     return s.connect_ex((host, port)) == 0
        try:
            if platform.system() == "Windows":
                result = subprocess.check_output(
                    f"netstat -ano | findstr {port}",
                    shell=True
                )
            else:
                # 使用 lsof 命令查看端口占用情况
                result = subprocess.check_output(["lsof", "-i", f":{str(port)}"], stderr=subprocess.DEVNULL)

            if b"LISTEN" in result:
                return True
        except subprocess.CalledProcessError:
            # lsof 如果没找到占用，会返回错误代码，说明没启动
            return False
        except Exception as e:
            return False

        return False

    def get_chrome_path(self):
        if self.config.get("chrome_path"):
            return self.config["chrome_path"]
        system = platform.system().lower()
        locations = self.config.get("binary_locations", {})
        return locations.get(system, "")

    def launch_chrome(self, port):
        """启动Chrome浏览器"""
        chrome_path = self.get_chrome_path()
        if not chrome_path or not os.path.exists(chrome_path):
            self.log(self.t("err_chrome_not_found"), "red")
            return False

        if platform.system() == "windows":
            user_data_dir = os.path.abspath(self.config.get("user_data_dir", "chrome_profile"))
        else:
            user_data_dir = os.path.expanduser(self.config.get("user_data_dir", "chrome_profile"))

        args = [
            chrome_path,
            f"--remote-debugging-port={port}",
            f"--user-data-dir={user_data_dir}",
            "--remote-allow-origins=*"
        ]
        args.extend(self.config.get("arguments", []))

        self.log(f"{self.t('launching_chrome_at')}: {chrome_path}")
        try:
            # 启动浏览器并
            subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            for _ in range(15):
                if self.stop_event.is_set(): break
                if self.is_port_open("127.0.0.1", port):
                    return True
                self.stop_event.wait(1)
            return False
        except Exception as e:
            self.log(f"{self.t('err_launch_chrome')}: {str(e)}", "red")
            return False

    def init_driver(self):
        try:
            port = self.config.get("remote_debugging_port", 9222)
            if not self.is_port_open("127.0.0.1", port):
                self.log(self.t("launching_new_chrome"), "blue")
                if not self.launch_chrome(port):
                    return False
            else:
                self.log(self.t("using_existing_chrome"), "blue")

            if self.stop_event.is_set(): return False

            chrome_options = Options()
            # 禁用闪退后的状态恢复提示
            chrome_options.add_experimental_option("prefs", {
                "profile.exit_type": "Normal",
                "profile.exited_cleanly": True,
            })
            chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            return True
        except Exception as e:
            self.log(f"{self.t('err_init_webdriver')}: {str(e)}", "red")
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None
            return False

    def run(self):
        from services.scraper_actions import ScraperActions
        try:
            self.log(f"{self.t('start_scrape')}: {self.sheet_name}", "blue")
            if not self.init_driver():
                return

            if self.stop_event.is_set(): return

            self.log(f"{self.t('scrape_data_received')}: {len(self.data)} {self.t('rows_to_process')}")

            actions_handler = ScraperActions(self.driver, self.log, self.t, stop_event=self.stop_event)

            idx = 0
            while idx < len(self.data):
                # for idx, row in enumerate(self.data):
                if self.stop_event.is_set():
                    self.log(self.t("scrape_interrupted"), "red")
                    break

                row = self.data[idx]
                # 使用 key 从字典中获取值
                step_id = row.get("id", f"Step {idx + 1}")
                action_type = row.get("action", "")
                wait_time_val = row.get("wait", 0)
                ignore_error = row.get("ignore_error", False)

                wait_time = float(wait_time_val) if wait_time_val and str(wait_time_val).strip() else 0

                self.log(f"[{idx + 1}/{len(self.data)}] {self.t('executing_step_idx')}: {step_id} ({action_type})")

                # 动态调用方法
                if action_type and hasattr(actions_handler, action_type):
                    # 通过ignore_error标志来判断是否需要忽略错误
                    try:
                        method = getattr(actions_handler, action_type)
                        method(row)
                    except Exception as e1:
                        if not ignore_error:
                            raise e1
                else:
                    self.log(f"{self.t('unknown_action')}: '{action_type}'", "orange")

                # 分段等待以响应停止信号
                if wait_time > 0 and action_type != "delay":
                    if self.stop_event.wait(wait_time):
                        break
                else:
                    self.stop_event.wait(0.5)

                # 如果下一个步骤被赋值，则跳转到相应的步骤
                if actions_handler.next_id != -1:
                    idx = actions_handler.next_id
                else:
                    idx += 1

            if not self.stop_event.is_set():
                self.log(self.t("scrape_completed"), "green")
        except Exception as e:
            self.log(f"{self.t('scrape_error')}: {str(e)}", "red")
        finally:
            if self.driver:
                try:
                    # 由于考虑到抓取的网站可能需要登录，所以程序关闭的时候不再主动关闭webdriver，如果程序抓取出错，请执行清除进程及缓存的按钮进行处理。
                    # self.log("正在关闭 WebDriver 资源...")
                    # self.driver.quit() # 关闭浏览器
                    pass
                except:
                    pass
                self.driver = None
            self.finished_signal.emit()

    def stop(self):
        self.stop_event.set()


class ScrapeService:
    """
    网页内容抓取逻辑服务类。
    """
    _instances = []

    def __init__(self, log_func=None, t=None):
        ScrapeService._instances.append(self)
        self.log_func = log_func
        self.t = t
        self.worker = None
        self.thread = None
        self.browser_config_path = os.path.join("config", "browser_config.json")
        self.config = FileService.load_json(self.browser_config_path)

    def log(self, msg, color="black"):
        if self.log_func:
            self.log_func(msg, color)

    def start_scrape(self, sheet_name, data):
        if self.thread and self.thread.is_alive():
            self.log(self.t("scrape_already_running"), "orange")
            return

        self.worker = ScrapeWorker(self.t, self.config, data, sheet_name)
        self.worker.log_signal.connect(self.log)
        self.worker.finished_signal.connect(self.on_finished)

        # 使用系统的 threading.Thread，并设置为 daemon = True
        # 这样主程序关闭时，该线程会自动退出
        self.thread = threading.Thread(target=self.worker.run, daemon=True)
        self.thread.start()

    def on_finished(self):
        """
        由于设计成程序退出也不关闭浏览器，则这个方法暂时不进行处理
        """

        pass

    def stop_scrape(self):
        if self.worker and self.thread and self.thread.is_alive():
            self.worker.stop()

            # 等待线程自然退出
            self.thread.join(timeout=3)
            self.log(self.t("stopped_scrape"), "red")
        else:
            self.log(self.t("no_scrape_running"))

    @classmethod
    def stop_all(cls):
        """静默停止所有运行中的抓取服务实例"""
        for instance in cls._instances:
            if instance.worker and instance.thread and instance.thread.is_alive():
                instance.worker.stop()
                # 根据用户要求，不在此处调用 quit() 或 terminate()
                instance.thread.join(timeout=2)

    def clear_chrome_cache(self):
        """清理 Chrome 浏览器缓存（删除用户数据目录）"""
        try:
            user_data_dir = os.path.abspath(self.config.get("user_data_dir", "chrome_profile"))
            if os.path.exists(user_data_dir):
                self.log(f"{self.t('clearing_cache_dir')}: {user_data_dir}...")
                # 递归删除目录
                shutil.rmtree(user_data_dir, ignore_errors=True)
                self.log(self.t("cache_cleared"), "green")
            else:
                self.log(self.t("no_cache_to_clear"), "orange")
            return True
        except Exception as e:
            self.log(f"{self.t('err_clear_cache')}: {str(e)}", "red")
            return False

    def kill_chrome_processes(self):
        """强制结束所有 Chrome 相关进程"""
        try:
            system = platform.system().lower()
            self.log(self.t("killing_chrome"))
            
            if system == "windows":
                # Windows 使用 taskkill
                subprocess.run(["taskkill", "/F", "/IM", "chrome.exe", "/T"], 
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["taskkill", "/F", "/IM", "chromedriver.exe", "/T"], 
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                # Linux/Mac 使用 pkill
                subprocess.run(["pkill", "-f", "chrome"], 
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["pkill", "-f", "chromedriver"], 
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            self.log(self.t("chrome_killed"), "green")
            return True
        except Exception as e:
            self.log(f"{self.t('err_kill_chrome')}: {str(e)}", "red")
            return False
