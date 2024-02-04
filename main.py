import os
import shutil
from datetime import datetime
import locale


class FileOrganizer:
    def __init__(self, source_directory, destination_directory):
        self.source_directory = source_directory
        self.destination_directory = destination_directory
        self.item_classifier = {'Corel': ['.cdr', '.cdt'],
                                'Word': ['.doc', '.docx', '.rtf', '.odt'],
                                'Excel': ['.xls', '.xlsx', '.xlsm'],
                                'PowerPoint': ['.ppt', '.pptx', '.ppsx'],
                                'Imagem': ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.tif', '.bmp'],
                                'Comprimido': ['.zip', '.rar', '.7z'],
                                'PDF': ['.pdf'],
                                'Fonts': ['.otf'],
                                'Logo': ['.ai', '.eps', '.psd', '.cmx'],
                                'Autocad': ['.cad', '.dwg'],
                                'Video': ['.avi', '.mkv', '.mp4', '.mpg', '.wmv'],
                                'Flash': ['.flv'],
                                'Audio': ['.mp3', '.aac', '.vob', '.wav'],
                                'Java': ['.jar'],
                                'Executavel': ['.exe', '.msi'],
                                'Imagem_de_disco': ['.iso'],
                                'Texto': ['.txt', '.log', '.ini'],
                                'Torrent': ['.torrent']
                                }
        self.anime_classifier = ['[SubsPlease]', '[EMBER]', '[Erai-raws]']

    def get_file_info(self, file_path):
        # Extracts file information: extension, year, and month
        modified_time = datetime.fromtimestamp(os.path.getmtime(file_path))
        # file_extension = file_path.split('.')[-1].lower() if '.' in file_path else 'unknown'
        file_apath, file_extension = os.path.splitext(file_path)
        if not file_extension:
            file_extension = 'noext'
        file_name = file_apath.split('/')
        return file_extension, modified_time.year, modified_time.month, file_name

    def organize_files(self):
        file_count = {}
        extensions_to_sort = set()

        # Add extensions to sort to the item classifier
        for _, extension in self.item_classifier.items():
            extensions_to_sort.update(extension)

        # Sort files based on extensions
        for root, dirs, files in os.walk(self.source_directory, topdown=False):
            for filename in files:
                file_path = os.path.join(root, filename)

                if os.path.isfile(file_path):
                    extension, year, month, file_name = self.get_file_info(file_path)

                    # Create destination directories if they don't exist
                    category = None
                    for key, extensions in self.item_classifier.items():
                        if extension in extensions:
                            category = key
                            break
                    if category is None:
                        category = "Other"

                    video_directory = os.path.join(self.destination_directory, category)
                    joined_directory = os.path.join(self.destination_directory, category, str(year))
                    month_number = f"{month:02d}"
                    month_name = datetime(2000, month, 1).strftime('%B')
                    final_directory = os.path.join(joined_directory, f"{month_number}_{month_name}")

                    os.makedirs(final_directory, exist_ok=True)
                    os.makedirs(video_directory, exist_ok=True)

                    # Handle files with the same name
                    base_name, ext = os.path.splitext(filename)
                    new_filename = filename
                    count = file_count.get(new_filename, 0)

                    while os.path.exists(os.path.join(final_directory, new_filename)):
                        count += 1
                        new_filename = f"{base_name}_{count}{ext}"

                    file_count[filename] = count

                    # Special sorting rules for the "Video" category
                    if category == "Video":
                        # Define your special sorting conditions here
                        if any(sub in file_name for sub in self.anime_classifier):
                            shutil.move(file_path, os.path.join(video_directory, new_filename))
                            print(f"Moved {filename} to {video_directory}")
                        else:
                            shutil.move(file_path, os.path.join(final_directory, new_filename))
                            print(f"Moved {filename} to {final_directory}")
                    else:
                        # For categories other than "Video", sort by time
                        shutil.move(file_path, os.path.join(final_directory, new_filename))
                    print(f"Moved {filename} to {final_directory}")

        # Remove empty directories in the source directory
        for root, dirs, files in os.walk(self.source_directory, topdown=False):
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                if not os.listdir(dir_path):
                    os.rmdir(dir_path)
                    print(f"Removed empty directory: {dir_path}")


if __name__ == "__main__":
    # Set the system language for directories names
    locale.setlocale(locale.LC_ALL, '')
    # system_language, _ = locale.getdefaultlocale()
    # locale.setlocale(locale.LC_TIME, system_language)

    def main():
        # main script
        source_directory = 'D:\\Source'
        destination_directory = 'D:\\Destiny'

        # source_directory = input("Please enter the SOURCE directory:\n")
        # destination_directory = input("Please enter the DESTINATION directory:\n")

        # Create an instance of FileOrganizer
        organizer = FileOrganizer(source_directory, destination_directory)
        # Call the organize_files method
        organizer.organize_files()


    main()
