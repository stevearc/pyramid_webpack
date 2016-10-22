Getting Started
===============
These instructions will get you up and running with a minimal Pyramid app and a
basic webpack configuration.

Set up the Pyramid app
----------------------
Skip this section if you already have a Pyramid server up and running. Set up a
virtualenv and create a new Pyramid project::

    virtualenv venv
    source venv/bin/activate
    pip install pyramid
    pcreate -s starter hello_world
    cd hello_world
    pip install -e .

You should be able to run the server with ``pserve development.ini`` and see it
working.

Install and configure pyramid_webpack
-------------------------------------
We're also going to install `pyramid_jinja2
<https://github.com/Pylons/pyramid_jinja2>`_ as the templating engine.

::

    pip install pyramid_jinja2 pyramid_webpack

Add the following to your development.ini file::

    # If this option already exists, append the values
    pyramid.includes = 
        pyramid_jinja2
        pyramid_webpack
    jinja2.extensions =
        pyramid_webpack.jinja2ext:WebpackExtension

    # Reloads file changes and requests wait while webpack is compiling
    webpack.debug = True
    # Directory containing the webpack bundles. Relative to your package root.
    webpack.bundle_dir = webpack/bundles
    # File containing the webpack stats. Relative to your package root.
    webpack.stats_file = webpack/stats.json

Set up webpack
--------------
You will need to have `Node <https://nodejs.org/en/download/>`_ installed and in
your PATH for the following steps.

::

  npm init
  npm install --save-dev webpack webpack-bundle-tracker babel babel-loader

Put the following into ``webpack.config.js``

.. code-block:: json

  var path = require("path")
  var BundleTracker = require('webpack-bundle-tracker')

  module.exports = {
    context: __dirname,

    entry: './assets/js/index',

    output: {
        path: path.resolve('./hello_world/webpack/bundles/'),
        filename: "[name]-[hash].js",
    },

    plugins: [
      new BundleTracker({filename: './hello_world/webpack/stats.json'}),
    ],

    module: {
      loaders: [
        {
          test: /\.js$/,
          exclude: /node_modules/,
          loader: 'babel-loader'
        },
      ],
    },

    resolve: {
      modulesDirectories: ['node_modules'],
      extensions: ['', '.js']
    },
  }

Create a javascript file to be built by webpack::

  mkdir -p assets/js/
  echo "var n = document.createElement('h1'); n.innerText = 'Javascript loaded'; document.body.appendChild(n);" > assets/js/index.js

Running everything
------------------
Run the Pyramid server with::

  pserve --reload development.ini

Run webpack with::

  ./node_modules/.bin/webpack --config webpack.config.js -d --progress --colors --watch

Using in templates
------------------
To render a bundle inside a Chameleon template, we're going to call
``get_bundle`` directly. Create a file called ``hello_world/templates/index.pt`` and add
the following::

  <!DOCTYPE html>
  <html>
    <head>
      <meta charset="UTF-8">
      <title>Example</title>
    </head>

    <body>
      <script type="text/javascript" tal:repeat="asset request.webpack().get_bundle('main')" src="${asset.url}"></script>
    </body>
  </html>

Then change the renderer in ``hello_world/views.py`` to be
``templates/index.pt``. When you reload the webpage it should now say
"Javascript Loaded".

To render a bundle in Jinja2, make a template called
``hello_world/templates/index.jinja2`` and add the following::

  <!DOCTYPE html>
  <html>
    <head>
      <meta charset="UTF-8">
      <title>Example</title>
    </head>

    <body>
      {% webpack 'main' %}
        <script type="text/javascript" src="{{ ASSET.url }}"></script>
      {% endwebpack %}
    </body>
  </html>

Then change the renderer in ``hello_world/views.py`` to be
``templates/index.jinja2``. When you reload the webpage it should now say
"Javascript Loaded".
