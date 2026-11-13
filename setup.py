from glob import glob

from setuptools import setup

package_name = 'landxml_viz'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
        ('share/' + package_name + '/rviz', glob('rviz/*.rviz')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Antti Kolu',
    description='Publishes LandXML / Inframodel TIN surfaces and breaklines as RViz markers.',
    license='Proprietary',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'landxml_publisher = landxml_viz.landxml_publisher:main',
        ],
    },
)
