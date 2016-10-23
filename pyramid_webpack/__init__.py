""" pyramid_webpack """
import os
import fnmatch
import posixpath
import re
import time

import json
import six
from pkg_resources import resource_stream
from pyramid.decorator import reify
from pyramid.settings import asbool, aslist


__version__ = '0.1.0'


SENTINEL = object()


@six.python_2_unicode_compatible
class StaticResource(object):
    """ Wrapper around a filepath or asset path """

    def __init__(self, path):
        self.path = path

    @classmethod
    def create(cls, path, root_package):
        """ Create a StaticResource, setting the package if needed """
        if ':' not in path and not path.startswith('/'):
            return cls("{0}:{1}".format(root_package, path))
        return cls(path)

    def open(self):
        """ Open a stream object to the resource data """
        if self.path.startswith('/'):
            # Absolute path
            filepath = self.path
            return open(filepath, 'r')
        else:
            # Asset specification
            package, filename = self.path.split(':')
            return resource_stream(package, filename)

    def __str__(self):
        return "Resource('{0}')".format(self.path)


class WebpackState(object):

    """ Wrapper for all webpack configuration and cached data """

    def __init__(self, settings, root_package_name=__package__, name='DEFAULT'):
        self.name = name
        self._settings = settings
        self._stats = None
        self.debug = asbool(self._get_setting('debug', False))
        self.static_view = asbool(self._get_setting('static_view', True,
                                                    inherit=False))
        bundle_dir = self._get_setting('bundle_dir', None, inherit=False)
        if bundle_dir is None:
            self.static_view_path = 'webpack-{0}'.format(name)
        elif ':' not in bundle_dir and not bundle_dir.startswith('/'):
            asset_spec = '{0}:{1}'.format(root_package_name, bundle_dir)
            self.static_view_path = asset_spec
        else:
            self.static_view_path = bundle_dir
        self.static_view_name = self._get_setting('static_view_name',
                                                  'webpack-{0}'.format(name),
                                                  inherit=False)
        stats_file_path = self._get_setting('stats_file', 'webpack-stats.json',
                                            inherit=False)
        self.stats_file = StaticResource.create(stats_file_path,
                                                root_package_name)
        self.timeout = float(self._get_setting('timeout', 0))
        self.ignore = aslist(self._get_setting('ignore',
                                               [r'*.hot-update.js', r'*.map']))
        ignore_re = aslist(self._get_setting('ignore_re', []))
        self.ignore_re = [re.compile(p) for p in ignore_re]

    def _get_setting(self, setting, default=None, name=None, inherit=True):
        """ Helper function to fetch settings, inheriting from the base """
        if name is None:
            name = self.name
        if name == 'DEFAULT':
            return self._settings.get('webpack.{0}'.format(setting), default)
        else:
            val = self._settings.get('webpack.{0}.{1}'.format(name, setting),
                                     SENTINEL)
            if val is SENTINEL:
                if inherit:
                    return self._get_setting(setting, default, 'DEFAULT')
                else:
                    return default
            else:
                return val

    def load_stats(self, cache=None, wait=None):
        """ Load and cache the webpack-stats file """
        if cache is None:
            cache = not self.debug
        if wait is None:
            wait = self.debug
        if not cache or self._stats is None:
            self._stats = self._load_stats()
            start = time.time()
            while wait and self._stats.get('status') == 'compiling':
                if self.timeout and (time.time() - start > self.timeout):
                    raise RuntimeError("Webpack {0!r} timed out while compiling"
                                       .format(self.stats_file.path))
                time.sleep(0.1)
                self._stats = self._load_stats()
        return self._stats

    def _load_stats(self):
        """ Load the webpack-stats file """
        for attempt in range(0, 3):
            try:
                with self.stats_file.open() as f:
                    return json.load(f)
            except ValueError:
                # If we failed to parse the JSON, it's possible that the
                # webpack process is writing to it concurrently and it's in a
                # bad state. Sleep and retry.
                if attempt < 2:
                    time.sleep(attempt * 0.2)
                else:
                    raise
            except IOError:
                raise IOError(
                    "Could not read stats file {0}. Make sure you are using the "
                    "webpack-bundle-tracker plugin" .format(self.stats_file))


class Webpack(object):

    """ Wrapper object for the public webpack API """

    def __init__(self, request, name='DEFAULT'):
        self.name = name
        self._request = request
        self.state = request.registry.webpack.get(name)
        if self.state is None:
            raise RuntimeError("Unknown webpack config {0!r}".format(name))

    @reify
    def stats(self):
        """ Load and cache the webpack stats file """
        return self.state.load_stats()

    def _chunk_filter(self, extensions):
        """ Create a filter from the extensions and ignore files """
        if isinstance(extensions, six.string_types):
            extensions = extensions.split()

        def _filter(chunk):
            """ Exclusion filter """
            name = chunk['name']
            if extensions is not None:
                if not any(name.endswith(e) for e in extensions):
                    return False
            for pattern in self.state.ignore_re:
                if pattern.match(name):
                    return False
            for pattern in self.state.ignore:
                if fnmatch.fnmatchcase(name, pattern):
                    return False
            return True
        return _filter

    def _add_url(self, chunk):
        """ Add a 'url' property to a chunk and return it """
        if 'url' in chunk:
            return chunk
        public_path = chunk.get('publicPath')
        if public_path:
            chunk['url'] = public_path
        else:
            fullpath = posixpath.join(self.state.static_view_path,
                                      chunk['name'])
            chunk['url'] = self._request.static_url(fullpath)
        return chunk

    def get_bundle(self, bundle_name, extensions=None):
        """ Get all the chunks contained in a bundle """
        if self.stats.get('status') == 'done':
            bundle = self.stats.get('chunks', {}).get(bundle_name, None)
            if bundle is None:
                raise KeyError('No such bundle {0!r}.'.format(bundle_name))
            test = self._chunk_filter(extensions)
            return [self._add_url(c) for c in bundle if test(c)]
        elif self.stats.get('status') == 'error':
            raise RuntimeError("{error}: {message}".format(**self.stats))
        else:
            raise RuntimeError(
                "Bad webpack stats file {0} status: {1!r}"
                .format(self.state.stats_file, self.stats.get('status')))


def get_webpack(request, name='DEFAULT'):
    """
    Get the Webpack object for a given webpack config.

    Called at most once per request per config name.
    """
    if not hasattr(request, '_webpack_map'):
        request._webpack_map = {}
    wp = request._webpack_map.get(name)
    if wp is None:
        wp = request._webpack_map[name] = Webpack(request, name)
    return wp


def includeme(config):
    """ Add pyramid_webpack methods and config to the app """
    settings = config.registry.settings
    root_package_name = config.root_package.__name__
    config.registry.webpack = {
        'DEFAULT': WebpackState(settings, root_package_name)
    }
    for extra_config in aslist(settings.get('webpack.configs', [])):
        state = WebpackState(settings, root_package_name, name=extra_config)
        config.registry.webpack[extra_config] = state

    # Set up any static views
    for state in six.itervalues(config.registry.webpack):
        if state.static_view:
            config.add_static_view(name=state.static_view_name,
                                   path=state.static_view_path)

    config.add_request_method(get_webpack, 'webpack')
