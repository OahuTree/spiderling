from services.file_service import FileService


class JsonService:
    """
    JSON 文件操作服务类，内部使用 FileService 统一处理。
    """

    @staticmethod
    def load_json(file_path, default_data=None):
        return FileService.load_json(file_path, default_data)

    @staticmethod
    def save_json(file_path, data):
        FileService.save_json(file_path, data)
