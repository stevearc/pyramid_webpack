Pyramid Webpack
===============
:Build: |build|_ |coverage|_
:Documentation: http://pyramid-webpack.readthedocs.io/
:Downloads: http://pypi.python.org/pypi/pyramid_webpack
:Source: https://github.com/stevearc/pyramid_webpack

.. |build| image:: https://travis-ci.org/stevearc/pyramid_webpack.png?branch=master
.. _build: https://travis-ci.org/stevearc/pyramid_webpack
.. |coverage| image:: https://coveralls.io/repos/github/stevearc/pyramid_webpack/badge.svg?branch=master
.. _coverage: https://coveralls.io/github/stevearc/pyramid_webpack?branch=master

A Pyramid extension for managing assets with Webpack.

Quick Start
-----------

Install `cookiecutter <https://cookiecutter.readthedocs.io/en/latest/installation.html>`__

Create a new project::

  $ cookiecutter gh:stevearc/pyramid-cookiecutter-webpack

Install and set up necessary packages::

  $ cd <your project>
  $ virtualenv env
  $ source env/bin/activate
  $ pip install --upgrade pip
  $ pip install -e .
  $ npm install

Start the webpack build::

  $ npm run watch

In a separate terminal, start the Pyramid server::

  $ pserve --reload development.ini
