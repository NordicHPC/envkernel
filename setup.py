import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="envkernel",
    version="0.0.2.dev0",
    author="Richard Darst",
    author_email="author@example.com",
    description="Jupyter kernels in docker, singularity, Lmod",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/NordicHPC/envkernel",
    #packages=setuptools.find_packages(),
    py_modules=["envkernel"],
    entry_points={
        'console_scripts': [
            'envkernel=envkernel:main',
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha",
        "Framework :: Jupyter",
    ],
)
