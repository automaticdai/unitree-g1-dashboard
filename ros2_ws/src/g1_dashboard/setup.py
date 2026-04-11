from setuptools import setup, find_packages
import os
from glob import glob

package_name = 'g1_dashboard'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/g1_dashboard']),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
        ('share/' + package_name + '/config', glob('config/*.yaml')),
        ('share/' + package_name + '/resource/styles', glob('resource/styles/*.qss')),
        ('share/' + package_name + '/resource/urdf', glob('resource/urdf/*.urdf')),
        ('share/' + package_name + '/resource/meshes', glob('resource/meshes/*')),
        ('share/' + package_name + '/resource/icons', glob('resource/icons/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='TODO',
    maintainer_email='todo@todo.com',
    description='Desktop dashboard for Unitree G1 humanoid robot control and visualization',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'dashboard = g1_dashboard.main:main',
        ],
    },
)
