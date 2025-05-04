from setuptools import setup, find_packages

setup(
    name='lyrics-search',
    version='1.2',
    author='tobias@randombytes',
    author_email='placeholder@example.com',
    description='Tool to quickly gather lyrics of songs',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/DasIstTobias/lyrics-search',
    packages=find_packages(),
    install_requires=[
        # placeholder
    ],
    entry_points={
        'console_scripts': [
            'lyrics-search=lyrics_search.main:main',
        ],
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.11',
)