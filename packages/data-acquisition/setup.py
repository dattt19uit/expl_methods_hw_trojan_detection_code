"""
Setup configuration for data_acquisition package.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="xai-data-acquisition",
    version="1.0.0",
    author="Paul Whitten, Francis Wolff, Chris Papachristou",
    author_email="pcw@case.edu",
    description="Trust-Hub circuit downloader for hardware trojan benchmarks",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/paulwhitten/expl_methods_hw_trojan_detection_code",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.28.0",
        "beautifulsoup4>=4.11.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "xai-download=data_acquisition.downloader.cli:main",
        ],
    },
)
