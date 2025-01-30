from setuptools import setup, find_packages

setup(
    name='sudoku',
    version='0.1',
    packages=find_packages(),  # Cela trouve automatiquement tous les packages
    install_requires=[
        'Flask==3.0.0',
        'numpy==1.24.3',
    ],
)