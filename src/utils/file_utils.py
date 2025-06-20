import os

class FileUtils:
    @staticmethod
    def ensure_dir(directory):
        os.makedirs(directory, exist_ok=True)

    @staticmethod
    def remove_file(file_path):
        if os.path.exists(file_path):
            os.remove(file_path)