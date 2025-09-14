from setuptools import setup

setup (
    name="git-clone",
    version=1.0,
    packages=["git_clone"],
    entry_points={
        "console_scripts": [
            "git-clone = git_clone.cli:main"
        ]
    }
)