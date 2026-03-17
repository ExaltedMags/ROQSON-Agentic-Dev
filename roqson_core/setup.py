from setuptools import setup, find_packages

setup(
    name="roqson_core",
    version="0.0.1",
    description="ROQSON Industrial Sales core app",
    author="ROQSON",
    packages=find_packages(where=".", include=["roqson_core*"]),
    zip_safe=False,
    include_package_data=True,
    python_requires=">=3.10",
)
