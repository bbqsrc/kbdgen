from setuptools import setup, find_packages
from kbdgen import __version__

with open("README.rst") as f:
    desc = f.read()

setup(
    name="kbdgen",
    version=__version__,
    description="Generate soft keyboards for mobile OSes and layouts for Windows, macOS and X11.",
    long_description=desc,
    url="https://github.com/bbqsrc/kbdgen",
    author="Brendan Molloy",
    author_email="brendan+pypi@bbqsrc.net",
    license="Apache-2.0",
    packages=find_packages(),
    keywords=["keyboard", "generator", "cldr"],
    include_package_data=True,
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
    ],
)
