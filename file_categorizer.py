
extension_types = {
    'Corel': ['.cdr', '.cdt'],
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
    'Torrent': ['.torrent'],
    'Other': []
}


class FileCategorizer:
    def __init__(self, file_info_list):
        self.file_info_list = file_info_list

    def categorize_files_by_extension(self):
        categorized_files = {category: [] for category in extension_types.keys()}

        for file_info in self.file_info_list:
            file_extension = file_info['file_extension']
            assigned_category = None

            for category, extensions in extension_types.items():
                if file_extension.lower() in extensions:
                    categorized_files[category].append(file_info)
                    break
            else:
                assigned_category = 'Other'  # Assign 'Other' category if no match found
                categorized_files[assigned_category].append(file_info)

        return categorized_files
