from setuptools import setup
import os
from glob import glob

package_name = 'ebsc_brain'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='EBSC Developer',
    maintainer_email='pss@ebsc.org',
    description='EBSC core logic: AI perception and Consensus',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'uav_node = ebsc_brain.uav_node:main',
            'truth_oracle_node = ebsc_brain.truth_oracle_node:main',
            'ebsc_logger = ebsc_brain.logger_node:main',  
        ],
    },
)