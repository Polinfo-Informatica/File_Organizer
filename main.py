import locale
from file_extractor import FileExtractor
from file_categorizer import FileCategorizer
from video_filter import VideoFilter
from files_manipulator import FolderCreator
from files_manipulator import FileMover


class FileManager:
    def __init__(self, input_dir, output_dir):
        self.input_dir = input_dir
        self.output_dir = output_dir

    def process_files(self):
        # Extract file information
        file_extractor = FileExtractor(self.input_dir)
        file_info_list = file_extractor.extract_file_info()

        # Categorize files by extension
        file_categorizer = FileCategorizer(file_info_list)
        categorized_files = file_categorizer.categorize_files_by_extension()

        # Apply video filter to categorize video files
        extract_subcategory(categorized_files['Video'])
        categorized_files['Video'] = VideoFilter.filter_video_files(categorized_files['Video'])

        # Create instances of FolderCreator and FileMover
        folder_creator = FolderCreator(categorized_files)
        file_mover = FileMover(categorized_files)

        # Create folder structure
        folder_creator.create_folder_structure(self.output_dir)

        # Move files to appropriate folders
        file_mover.move_files(self.output_dir)


if __name__ == "__main__":
    # Set the system locale
    locale.setlocale(locale.LC_ALL, '')

    # Define the input and output directories
    input_dir = 'path_to_input_directory'
    output_dir = 'path_to_output_directory'

    # Create FileManager instance and process files
    file_manager = FileManager(input_dir, output_dir)
    file_manager.process_files()
