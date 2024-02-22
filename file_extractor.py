import os
import datetime
import locale


class FileExtractor:
    def __init__(self, folder_path):
        self.folder_path = folder_path
        # Set locale to user's default locale

    def extract_file_info(self):
        file_info_list = []
        for root, dirs, files in os.walk(self.folder_path):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                file_size = os.path.getsize(file_path)
                file_extension = os.path.splitext(file_name)[1]
                file_name_without_extension = os.path.splitext(file_name)[0]
                file_name_only = os.path.basename(file_name_without_extension)
                modification_time = os.path.getmtime(file_path)
                creation_time = os.path.getctime(file_path)

                # Convert modification and creation time to datetime objects
                modification_time = datetime.datetime.fromtimestamp(modification_time)
                creation_time = datetime.datetime.fromtimestamp(creation_time)

                file_info = {
                    'file_path': file_path,
                    'file_name_with_path': file_name,
                    'file_name_only': file_name_only,
                    'file_size': file_size,
                    'file_extension': file_extension,
                    'file_name_without_extension': file_name_without_extension,
                    'modification_time': modification_time.strftime('%c'),  # Format based on locale
                    'creation_time': creation_time.strftime('%c')  # Format based on locale
                }
                file_info_list.append(file_info)
        return file_info_list
