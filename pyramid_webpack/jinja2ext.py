""" Jinja2 extension for pyramid_webpack """
from __future__ import unicode_literals

import six
from pyramid.threadlocal import get_current_request

from jinja2 import nodes
from jinja2.ext import Extension


class WebpackExtension(Extension):

    """
    Extension for jinja2.

    Examples
    --------
    ::

        {% webpack 'main' %}
            <link rel="stylesheet" type="text/css" href="{{ ASSET.url }}">
        {% endwebpack %}

    ::

        {% webpack 'other_config:main', 'js', 'js.gz' %}
            <script type="text/javascript" src="{{ ASSET.url }}"></script>
        {% endwebpack %}

    """

    tags = set(['webpack'])

    def parse(self, parser):
        # the first token is the token that started the tag.  In our case
        # we only listen to ``'webpack'`` so this will be a name token with
        # `webpack` as value.  We get the line number so that we can give
        # that line number to the nodes we create by hand.
        lineno = six.next(parser.stream).lineno
        ctx_ref = nodes.ContextReference()

        # Parse a single expression that is the 'bundle' or 'config:bundle'
        args = [ctx_ref, parser.parse_expression()]

        # if there is a comma, the user provided an 'extensions' arg
        if parser.stream.skip_if('comma'):
            args.append(parser.parse_expression())
        else:
            args.append(nodes.Const(None))

        # now we parse the body of the cache block up to `endwebpack` and
        # drop the needle (which would always be `endwebpack` in that case)
        body = parser.parse_statements(['name:endwebpack'], drop_needle=True)

        call_args = [nodes.Name('ASSET', 'store')]

        return nodes.CallBlock(self.call_method('_get_graph', args), call_args,
                               [], body).set_lineno(lineno)

    def _get_graph(self, ctx, bundle, extensions, caller=None):
        """ Run a graph and render the tag contents for each output """
        request = ctx.get('request')
        if request is None:
            request = get_current_request()
        if ':' in bundle:
            config_name, bundle = bundle.split(':')
        else:
            config_name = 'DEFAULT'
        webpack = request.webpack(config_name)
        assets = (caller(a) for a in webpack.get_bundle(bundle, extensions))
        return ''.join(assets)
