from setuptools import setup, find_packages
from pathlib import Path

# Read long description from README
def read_long_description():
    return Path('README.md').read_text(encoding='utf-8')

# Read requirements from requirements file
def read_requirements(filename):
    with open(filename, 'r') as file:
        return [line.strip() for line in file 
                if line.strip() and not line.startswith('#')]

setup(
    name='gamdl',
    version='0.1.0',
    
    # Metadata
    author='Your Name',
    author_email='your.email@example.com',
    description='Advanced Music Downloader and Manager',
    long_description=read_long_description(),
    long_description_content_type='text/markdown',
    
    # Project URLs
    url='https://github.com/yourusername/gamdl',
    project_urls={
        'Bug Tracker': 'https://github.com/yourusername/gamdl/issues',
        'Documentation': 'https://github.com/yourusername/gamdl/docs',
        'Source Code': 'https://github.com/yourusername/gamdl',
    },
    
    # Packaging
    packages=find_packages(exclude=['tests*', 'docs*']),
    include_package_data=True,
    package_data={
        'gamdl': [
            'config/*.yaml',
            'templates/*.html',
            'static/*',
            'locales/*',
        ]
    },
    
    # Dependencies
    install_requires=[
        # Core dependencies
        'spotipy>=2.19.0',
        'youtube-dl>=2021.12.17',
        'mutagen>=1.45.1',
        'python-telegram-bot>=13.7',
        'requests>=2.26.0',
        'python-dotenv>=0.19.0',
        
        # Additional utilities
        'rich>=10.12.0',
        'click>=8.0.3',
        'colorama>=0.4.4',
    ],
    
    # Development Dependencies
    extras_require={
        'dev': [
            'pytest>=6.2.5',
            'black>=21.9b0',
            'flake8>=3.9.2',
            'mypy>=0.910',
            'coverage>=5.5',
        ],
        'docs': [
            'sphinx>=4.1.2',
            'sphinx-rtd-theme>=0.5.2',
        ],
    },
    
    # Entry Points (CLI)
    entry_points={
        'console_scripts': [
            'gamdl=gamdl.cli:main',
            'gamdl-telegram=gamdl.telegram_bot:start_bot',
        ],
    },
    
    # Classifiers
    classifiers=[
        # Maturity
        'Development Status :: 3 - Alpha',
        
        # Audience
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        
        # License
        'License :: OSI Approved :: MIT License',
        
        # Python Versions
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        
        # Topics
        'Topic :: Multimedia :: Sound/Audio',
        'Topic :: Internet :: WWW/HTTP',
        
        # Operating System
        'Operating System :: OS Independent',
    ],
    
    # Python Requirements
    python_requires='>=3.8',
    
    # Keywords for discoverability
    keywords='music downloader spotify youtube telegram audio',
    
    # Platform specifics
    platforms=['Windows', 'macOS', 'Linux'],
)
