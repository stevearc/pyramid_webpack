""" Setup file """
import os

from setuptools import setup, find_packages


HERE = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(HERE, 'README.rst')).read()
CHANGES = open(os.path.join(HERE, 'CHANGES.rst')).read()

REQUIREMENTS = [
    'pyramid',
    'six',
]

TEST_REQUIREMENTS = [
    'nose',
    'pyramid_jinja2',
    'webtest',
]

if __name__ == "__main__":
    setup(
        name='pyramid_webpack',
        version='0.1.0',
        description='Pyramid extension for managing assets with Webpack.',
        long_description=README + '\n\n' + CHANGES,
        classifiers=[
            'Development Status :: 4 - Beta',
            'Framework :: Pyramid',
            'Intended Audience :: Developers',
            'License :: OSI Approved :: MIT License',
            'Operating System :: OS Independent',
            'Programming Language :: Python',
            'Programming Language :: Python :: 2',
            'Programming Language :: Python :: 2.6',
            'Programming Language :: Python :: 2.7',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.3',
            'Programming Language :: Python :: 3.4',
            'Programming Language :: Python :: 3.5',
        ],
        author='Steven Arcangeli',
        author_email='stevearc@stevearc.com',
        url='http://github.com/stevearc/pyramid_webpack',
        keywords='pyramid webpack assets',
        license='MIT',
        platforms='any',
        include_package_data=True,
        packages=find_packages(exclude=('tests',)),
        install_requires=REQUIREMENTS,
        tests_require=REQUIREMENTS + TEST_REQUIREMENTS,
    )
