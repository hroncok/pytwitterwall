from setuptools import setup, find_packages


with open('README.rst') as f:
    long_description = ''.join(f.readlines())

NAME = 'pytwitterwall'

setup(
    name=NAME,
    version='0.3',
    description='Twitter wall for console and web',
    long_description=long_description,
    author='Miro Hrončok',
    author_email='miro@hroncok.cz',
    keywords='twitter',
    license='MIT',
    url='https://github.com/hroncok/pytwitterwall',
    install_requires=['click', 'Flask', 'Jinja2', 'requests'],
    packages=find_packages(),
    package_data={NAME: ['templates/*.html']},
    entry_points={
        'console_scripts': [
            '{p} = {p}.cli:cli'.format(p=NAME),
        ],
    },
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3 :: Only',
    ],
)
