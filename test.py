import os

file_path = '/Users/Programs/Directory/prog.ram1.csv'

file_apath, file_extension = os.path.splitext(file_path)
if not file_extension:
    file_extension = 'noext'
file_name = file_apath.split('/')

print(f"\n\nfile_path = {file_path}\n\nfile_apath = {file_apath}\n\nfile_extension = {file_extension}\n\n"
      f"file_name = {file_name[-1]}")
