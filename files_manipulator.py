import os
import shutil
from dateutil import parser


class FileMover:
    def __init__(self, categorized_files):
        self.categorized_files = categorized_files

    def move_files(self, base_dir):
        for category, files in self.categorized_files.items():
            for file_info in files:
                subcategory = file_info.get('subcategory', '')
                if category == 'Video':
                    dest_dir = os.path.join(base_dir, category, subcategory)
                else:
                    modification_time = parser.parse(file_info['modification_time'])
                    year = modification_time.year
                    month = f"{modification_time.month:02d}-{modification_time.strftime('%B')}"
                    dest_dir = os.path.join(base_dir, category, str(year), month)

                os.makedirs(dest_dir, exist_ok=True)

                src_file_path = file_info['file_path']
                dest_file_path = os.path.join(dest_dir, os.path.basename(src_file_path))
                shutil.move(src_file_path, dest_file_path)


class FolderCreator:
    def __init__(self, categorized_files):
        self.categorized_files = categorized_files

    def create_folder_structure(self, base_dir):
        for category, files in self.categorized_files.items():
            for file_info in files:
                subcategory = file_info.get('subcategory', '')
                if category == 'Video':
                    dest_dir = os.path.join(base_dir, category, subcategory)
                else:
                    modification_time = parser.parse(file_info['modification_time'])
                    year = modification_time.year
                    month = f"{modification_time.month:02d}-{modification_time.strftime('%B')}"
                    dest_dir = os.path.join(base_dir, category, str(year), month)

                os.makedirs(dest_dir, exist_ok=True)
