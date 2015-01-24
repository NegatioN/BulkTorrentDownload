__author__ = 'NegatioN'

import os
import shutil

#creates a folder within current working dir
#returns path of dir
def createFolder(name, path): #name of folder, and a default sub-folder you want to add
    path=os.getcwd() + '\\' + path + '\\' + name
    if not os.path.isdir(path):
        os.makedirs(path)
    return path