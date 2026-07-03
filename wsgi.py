import sys
import os

project_home = '/home/pranavcj5555/Amman-studio'
if project_home not in sys.path:
    sys.path = [project_home] + sys.path

os.chdir(project_home)

from app import app as application
