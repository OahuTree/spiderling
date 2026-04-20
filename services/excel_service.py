from services.file_service import FileService

class ExcelService:
    """
    Excel 操作服务类，内部使用 FileService 统一处理。
    """
    
    @staticmethod
    def load_excel(file_path, fields_config=None):
        return FileService.load_excel(file_path, fields_config)

    @staticmethod
    def save_excel(file_path, data, fields, t=None):
        FileService.save_excel(file_path, data, fields, t)

    @staticmethod
    def ensure_template(file_path, fields, t=None):
        FileService.ensure_excel_template(file_path, fields, t)
