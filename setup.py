import setuptools

# Get version
print("in setup.py")
main_ns = {}
with open('envkernel.py') as ver_file:
    exec(ver_file.read(), main_ns)

print(main_ns['version_info'], main_ns['__version__'])


with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="envkernel",
    version=main_ns['__version__'],
    author="Richard Darst",
    author_email="rkd@zgib.net",
    description="Jupyter kernels manipulation and in other environments (docker, Lmod, etc.)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/NordicHPC/envkernel",
    #packages=setuptools.find_packages(),
    py_modules=["envkernel"],
    keywords='jupyter kernelspec',
    python_requires='>=3.5',
    entry_points={
        'console_scripts': [
            'envkernel=envkernel:main',
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Framework :: Jupyter",
        "Environment :: Console",
        "Intended Audience :: System Administrators",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
    ],
)
