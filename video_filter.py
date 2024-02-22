class VideoFilter:
    def __init__(self, file_name, extract_subcategory):
        self.file_name = file_name
        self.extract_subcategory = extract_subcategory

    def extract_subcategory(self, file_name):
        # Find the index of the first ']'
        idx_close_bracket = file_name.find(']')
        if idx_close_bracket != -1:
            # Find the index of the first non-space character after ']'
            idx_first_non_space = idx_close_bracket + 1
            while idx_first_non_space < len(file_name) and file_name[idx_first_non_space] == ' ':
                idx_first_non_space += 1

            # Find the index of the first '-' after the first non-space character
            idx_dash = file_name.find('-', idx_first_non_space)

            # Extract the subcategory based on the defined rules
            if idx_dash != -1:
                subcategory = file_name[idx_first_non_space:idx_dash].strip()
            else:
                subcategory = file_name[idx_first_non_space:].strip()

            return subcategory
        else:
            return None
