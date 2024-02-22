import locale
from file_extractor import FileExtractor
from file_categorizer import FileCategorizer
from video_filter import VideoFilter

if __name__ == "__main__":
    # Set the locale based on the user's default locale
    default_locale = locale.getdefaultlocale()
    if default_locale[0]:
        locale.setlocale(locale.LC_TIME, default_locale)

    folder_path = input("Enter folder path: ")

    # Extract file information
    file_extractor = FileExtractor(folder_path)
    file_info_list = file_extractor.extract_file_info()

    # Categorize files by extension
    file_categorizer = FileCategorizer(file_info_list)
    categorized_files = file_categorizer.categorize_files_by_extension()

    # Print categorized files
    for category, files in categorized_files.items():
        print(f"Category: {category}")
        for file_info in files:
            print(f"\tFile: {file_info['file_path']}, "
                  f"Modification Time: {file_info['modification_time']}, "
                  f"Creation Time: {file_info['creation_time']}")

    # Filter video files
    video_files = VideoFilter.filter_video_files(categorized_files)

    # Print filtered video files
    print("Video Files:")
    for file_info in video_files:
        print(f"\tFile: {file_info['file_name_with_path']}, "
              f"Modification Time: {file_info['modification_time']}, "
              f"Creation Time: {file_info['creation_time']}")
