#!/usr/bin/env python
# Author: Ashutosh Narayan
# Email: aashutoshnarayan@gmail.com

# Create subdirectory under app/ directory

def main():
 import os,sys,glob,time

 dirName3 = '../app/data'
 file1 = '../app/japanese_name_location_dict.txt'
 file2 = '../app/chinese_family_name_dict.txt'
 file3 = '../app/utils/utils.py'

 #Create subdirectories if they don't exist
 if not os.path.exists(dirName3):
     os.mkdir(dirName3,0755)
     print ("Directory", dirName3, "is created")
 else:
     print ("Directory", dirName3, "already exists")

 if os.path.exists(file1):
     os.system('mv ../app/japanese_name_location_dict.txt ../app/data/')
 else:
     print ("File is moved")
 if os.path.exists(file2):
     os.system('mv ../app/chinese_family_name_dict.txt ../app/data/')
 else:
     print ("File is moved")

if __name__ == '__main__':
    main()
