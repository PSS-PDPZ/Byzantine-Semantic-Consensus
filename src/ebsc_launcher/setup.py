# 文件路径: ebsc_project_ws/src/ebsc_launcher/setup.py
from setuptools import setup
import os
from glob import glob

package_name = 'ebsc_launcher'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob(os.path.join('launch', '*.launch.py'))),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='pss',
    maintainer_email='pss@todo.todo',
    description='Top-level launch file for EBSC experiments',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
        ],
    },
)