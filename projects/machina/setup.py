from setuptools import setup, find_packages

setup(
    name="research-lab",
    version="0.1.0",
    description="Autonomous Multi-Agent Research Laboratory",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "research-lab=cli.main:main",
        ],
    },
    python_requires=">=3.10",
)
