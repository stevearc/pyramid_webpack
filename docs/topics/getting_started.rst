Getting Started
===============
Install `cookiecutter <https://cookiecutter.readthedocs.io/en/latest/installation.html>`_

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
