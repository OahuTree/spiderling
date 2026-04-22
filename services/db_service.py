import os
from services.file_service import FileService


class DBService:
    """
    数据库配置服务类，负责数据库配置的加载、保存及连接字符串生成。
    内部使用 FileService 进行文件操作。
    """

    @staticmethod
    def get_config_path():
        """
        获取数据库配置文件的完整路径。
        读取 config/db_path_config.json 中的目录设置，默认为 config。
        支持 '~' 符号（用户家目录）。
        """
        path_config = DBService.load_path_config()
        config_dir = path_config.get("config_dir", "config")
        if not config_dir:
            config_dir = "config"

        # 自动处理 ~ 符号，将其扩展为用户家目录
        expanded_dir = os.path.expanduser(config_dir)
        return os.path.join(expanded_dir, "db_config.json")

    @staticmethod
    def load_path_config():
        """
        加载记录数据库配置目录的文件。
        """
        path_config_file = os.path.join("config", "db_path_config.json")
        return FileService.load_json(path_config_file, default_data={"config_dir": "config"})

    @staticmethod
    def save_path_config(config_dir):
        """
        保存数据库配置所在的目录。
        """
        path_config_file = os.path.join("config", "db_path_config.json")
        FileService.save_json(path_config_file, {"config_dir": config_dir})

    @staticmethod
    def load_config():
        """
        加载数据库配置。
        """
        config_path = DBService.get_config_path()
        return FileService.load_json(config_path, default_data={"databases": [], "current_index": 0})

    @staticmethod
    def save_config(config_data):
        """
        保存数据库配置。
        """
        config_path = DBService.get_config_path()
        FileService.save_json(config_path, config_data)

    @staticmethod
    def generate_conn_string(db_type, host, port, db_name, user, pwd, params=""):
        """
        根据参数生成 SQLAlchemy 格式的连接字符串。
        """
        return FileService.generate_conn_string(db_type, host, port, db_name, user, pwd, params)

    @staticmethod
    def test_connection(conn_string, table_name=None):
        """
        测试数据库连接及表是否存在。
        """
        from sqlalchemy import create_engine, inspect
        try:
            # 创建数据库引擎
            engine = create_engine(conn_string)
            # 尝试连接
            with engine.connect() as connection:
                if table_name:
                    inspector = inspect(engine)
                    tables = inspector.get_table_names()
                    if table_name not in tables:
                        return False, f"连接成功，但未找到表: {table_name}"
                return True, "连接测试成功！"
        except Exception as e:
            return False, f"连接失败: {str(e)}"

    @staticmethod
    def save_dataframe(df, table_name, if_exists='append', conn_string=None):
        """
        将 DataFrame 保存到数据库。
        如果未提供 conn_string，则从配置文件自动获取。
        """
        from sqlalchemy import create_engine
        try:
            # 如果没有传入连接字符串，则自动读取
            if not conn_string:
                conn_string = FileService.get_db_conn_string()

            if not conn_string:
                return False, "Error: No database connection string configured."

            # 创建数据库引擎
            engine = create_engine(conn_string)
            # 使用 pandas 的 to_sql 方法保存数据
            # index=False 表示不保存索引列
            df.to_sql(table_name, engine, if_exists=if_exists, index=False)
            return True, "Data committed successfully."
        except Exception as e:
            return False, f"Database error: {str(e)}"

    @staticmethod
    def get_table_columns(table_name, conn_string=None):
        """
        获取数据库表的列名列表。
        """
        from sqlalchemy import create_engine, inspect
        try:
            if not conn_string:
                conn_string = FileService.get_db_conn_string()
            if not conn_string: return []

            engine = create_engine(conn_string)
            inspector = inspect(engine)
            columns = [c["name"] for c in inspector.get_columns(table_name)]
            return columns
        except:
            return []

    @staticmethod
    def fetch_data(table_name, limit=100, sort_field=None, sort_order="ASC", conn_string=None):
        """
        从数据库查询数据，适配不同数据库方言。
        """
        import pandas as pd
        from sqlalchemy import create_engine, text
        try:
            if not conn_string:
                conn_string = FileService.get_db_conn_string()
            if not conn_string: return None, "未配置数据库连接"

            engine = create_engine(conn_string)
            dialect = engine.dialect.name

            # 处理表名和字段名的转义
            def quote(name):
                if dialect == 'mssql': return f"[{name}]"
                if dialect == 'mysql': return f"`{name}`"
                return f'"{name}"'

            safe_table = quote(table_name)
            order_clause = ""
            if sort_field:
                order_clause = f" ORDER BY {quote(sort_field)} {sort_order}"

            if dialect == 'mssql':
                # SQL Server 使用 TOP
                query = f"SELECT TOP {limit} * FROM {safe_table}{order_clause}"
            elif dialect == 'oracle':
                # Oracle 使用 ROWNUM 或 OFFSET/FETCH
                if order_clause:
                    query = f"SELECT * FROM (SELECT * FROM {safe_table}{order_clause}) WHERE ROWNUM <= {limit}"
                else:
                    query = f"SELECT * FROM {safe_table} WHERE ROWNUM <= {limit}"
            else:
                # MySQL, PostgreSQL, SQLite 使用 LIMIT
                query = f"SELECT * FROM {safe_table}{order_clause} LIMIT {limit}"

            with engine.connect() as conn:
                df = pd.read_sql(text(query), conn)
            return df, "Success"
        except Exception as e:
            return None, str(e)
