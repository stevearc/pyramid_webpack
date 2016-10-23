.. _templates:

Rendering bundles into templates
================================

Jinja2
------
Rendering bundles into jinja2 uses the ``webpack`` tag.

.. code-block:: jinja

    {% webpack 'main' %}
      <script type="text/javascript" src="{{ ASSET.url }}"></script>
    {% endwebpack %}

Inside of the ``webpack`` block you will have access to an ``ASSET`` variable
that has a ``url``, ``name``, and ``path``. The text inside of the block will be
repeated once per chunk that is in the bundle.

To use a different webpack config, prefix the name of the bundle with that
config name and a colon:

.. code-block:: jinja

    {% webpack 'other_config:mybundle' %}
      <script type="text/javascript" src="{{ ASSET.url }}"></script>
    {% endwebpack %}
    
And if you would like to filter the bundle by one or more file extensions, you
can pass that in as a second argument (space delimited string).

.. code-block:: jinja

    {% webpack 'mybundle', '.js .js.gz' %}
      <script type="text/javascript" src="{{ ASSET.url }}"></script>
    {% endwebpack %}

Chameleon
---------
Chameleon templates should just make a call directly to the ``get_bundle()``
method.

.. code-block:: genshi

    <script type="text/javascript"
      tal:repeat="asset request.webpack().get_bundle('main')"
      src="${asset.url}">
    </script>

To use a different webpack config, pass in the name of that config to ``request.webpack()``:

.. code-block:: genshi

    <script type="text/javascript"
      tal:repeat="asset request.webpack('other_config').get_bundle('main')"
      src="${asset.url}">
    </script>

And if you would like to filter the bundle by one or more file extensions, you
can pass them in as the second argument to ``get_bundle()``:

.. code-block:: genshi

    <script type="text/javascript"
      tal:repeat="asset request.webpack().get_bundle('main', ['.js', '.js.gz'])"
      src="${asset.url}">
    </script>
