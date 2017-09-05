""" Tests for pyramid_webpack """
import os
import inspect
import re

import json
import shutil
import tempfile
import webtest
from mock import MagicMock
from pyramid.config import Configurator
from pyramid.renderers import render_to_response
from six.moves.queue import Queue, Empty  # pylint: disable=E0401
from threading import Thread

from pyramid_webpack import WebpackState, Webpack, StaticResource


try:
    import unittest2 as unittest  # pylint: disable=E0401
except ImportError:
    import unittest


def load_stats(state, queue, *args, **kwargs):
    """ Load stats and put it into a queue """
    # Put a sentinel in the queue when the thread starts
    queue.put(object())
    stats = state.load_stats(*args, **kwargs)
    queue.put(stats)


def run_load_stats(state, *args, **kwargs):
    """ Run load_stats() in a thread """
    queue = Queue()
    thread_args = [state, queue]
    thread_args.extend(args)
    thread = Thread(target=load_stats, args=thread_args, kwargs=kwargs)
    thread.daemon = True
    thread.start()
    # Wait until the thread is definitely started
    queue.get(True)
    return queue


class TempDirTest(unittest.TestCase):

    """ Test class that provides filesystem helpers """

    def setUp(self):
        super(TempDirTest, self).setUp()
        self._tempdir = tempfile.mkdtemp()

    def tearDown(self):
        super(TempDirTest, self).tearDown()
        shutil.rmtree(self._tempdir)

    def _write(self, filename, data):
        """ Write json data to a file """
        fullpath = os.path.join(self._tempdir, filename)
        with open(fullpath, 'w') as ofile:
            json.dump(data, ofile)
        return fullpath


class TestWebpackState(TempDirTest):
    """ Tests for the WebpackState """

    def test_load_stats(self):
        """ State loads stats from a json file """
        data = {'a': 'b'}
        stats_file = self._write('stats.json', data)
        settings = {
            'webpack.stats_file': stats_file,
        }
        state = WebpackState(settings)
        stats = state.load_stats()
        self.assertEqual(stats, data)

    def test_load_stats_resource_stream(self):
        """
        State loads stats from a json file specified in a:b/c.json notation

        Tests the regression where loading the stats file specified in the
        notation didn't work for Python 3.5.
        """
        settings = {
            'webpack.stats_file': 'tests:test-stats.json',
        }
        state = WebpackState(settings)
        stats = state.load_stats()
        self.assertEqual(stats, {'a': 'b'})

    def test_missing_stats(self):
        """ raise IOError if stats file is missing """
        state = WebpackState({})
        with self.assertRaises(IOError):
            state.load_stats()

    def test_cache_stats(self):
        """ When cache=True, cache the stats file """
        data = {'a': 'b'}
        stats_file = self._write('stats.json', data)
        settings = {
            'webpack.stats_file': stats_file,
        }
        state = WebpackState(settings)
        stats = state.load_stats(cache=True)
        self.assertEqual(data, stats)
        with open(stats_file, 'w') as ofile:
            json.dump({'b': 'c'}, ofile)
        second_stats = state.load_stats(cache=True)
        self.assertEqual(second_stats, stats)

    def test_no_cache_stats(self):
        """ When cache=False, don't cache the stats file """
        stats_file = self._write('stats.json', {'a': 'b'})
        settings = {
            'webpack.stats_file': stats_file,
        }
        state = WebpackState(settings)
        state.load_stats(cache=False)
        data = {'b': 'c'}
        with open(stats_file, 'w') as ofile:
            json.dump(data, ofile)
        stats = state.load_stats(cache=False)
        self.assertEqual(stats, data)

    def test_multiple_configs(self):
        """ Multiple webpack states can have their own configs """
        settings = {
            'webpack.stats_file': 'foo',
            'webpack.other.stats_file': 'bar',
        }
        state = WebpackState(settings)
        self.assertTrue(state.stats_file.path.endswith(':foo'))
        other_state = WebpackState(settings, name='other')
        self.assertTrue(other_state.stats_file.path.endswith(':bar'))

    def test_no_wait_for_compile(self):
        """ The load_stats() call doesn't block if wait=False """
        data = {'status': 'compiling'}
        stats_file = self._write('stats.json', data)
        settings = {
            'webpack.stats_file': stats_file,
        }
        state = WebpackState(settings)
        queue = run_load_stats(state, wait=False)
        # Blocks & doesn't raise an exception
        stats = queue.get(True, 0.1)
        self.assertEqual(stats, data)

    def test_wait_for_compile(self):
        """ The load_stats() call blocks until webpack is done compiling """
        stats_file = self._write('stats.json', {'status': 'compiling'})
        settings = {
            'webpack.stats_file': stats_file,
        }
        state = WebpackState(settings)
        queue = run_load_stats(state, wait=True)
        with self.assertRaises(Empty):
            queue.get(True, 0.1)

        stats = {'status': 'done'}
        with open(stats_file, 'w') as ofile:
            json.dump(stats, ofile)
        data = queue.get(True, 5)
        self.assertEqual(data, stats)

    def test_compile_timeout(self):
        """ The load_stats() call will timeout if compile takes too long """
        stats_file = self._write('stats.json', {'status': 'compiling'})
        settings = {
            'webpack.stats_file': stats_file,
            'webpack.timeout': 0.5,
        }
        state = WebpackState(settings)
        with self.assertRaises(RuntimeError):
            state.load_stats(wait=True)

    def test_load_bad_data(self):
        """ load_stats() raises ValueError if json data is bad """
        stats_file = self._write('stats.json', {})
        with open(stats_file, 'a') as ofile:
            ofile.write('aaaaa')
        settings = {
            'webpack.stats_file': stats_file,
        }
        state = WebpackState(settings)
        with self.assertRaises(ValueError):
            state.load_stats()

    def test_abs_static_view(self):
        """ Absolute bundle directory paths are stored unmodified """
        settings = {
            'webpack.bundle_dir': '/foo/bar/baz',
        }
        state = WebpackState(settings)
        self.assertEqual(state.static_view_path, '/foo/bar/baz')

    def test_unspecified_relative_bundle(self):
        """ Relative bundle_dir paths with no package are given one """
        settings = {
            'webpack.bundle_dir': 'bundles',
        }
        state = WebpackState(settings, 'mypackage')
        self.assertEqual(state.static_view_path, 'mypackage:bundles')

    def test_static_package_resource(self):
        """ StaticResource can load a package resource """
        resource = StaticResource('pyramid_webpack:jinja2ext.py')
        import pyramid_webpack.jinja2ext
        with resource.open() as i:
            self.assertEqual(i.read().decode('utf-8'),
                             inspect.getsource(pyramid_webpack.jinja2ext))

    def test_future_expire(self):
        """ cache_max_age = future uses 10 year expiration """
        settings = {
            'webpack.cache_max_age': 'future',
        }
        state = WebpackState(settings, 'mypackage')
        self.assertTrue(state.cache_max_age > 100000)

    def test_custom_expire(self):
        """ cache_max_age can specify view expiration """
        settings = {
            'webpack.cache_max_age': '1234',
        }
        state = WebpackState(settings, 'mypackage')
        self.assertEqual(state.cache_max_age, 1234)

    def test_default_expire_debug(self):
        """ cache_max_age defaults to None in debug mode """
        settings = {
            'webpack.debug': 'true',
        }
        state = WebpackState(settings, 'mypackage')
        self.assertIsNone(state.cache_max_age)

    def test_default_expire(self):
        """ cache_max_age defaults to 3600 in non-debug mode """
        settings = {
            'webpack.debug': 'false',
        }
        state = WebpackState(settings, 'mypackage')
        self.assertEqual(state.cache_max_age, 3600)


class TestWebpack(unittest.TestCase):

    """ Test class for the Webpack functions """

    def setUp(self):
        super(TestWebpack, self).setUp()
        self.request = MagicMock()
        self.webpack = Webpack(self.request)
        self.webpack.state = WebpackState({})
        self.stats = {
            'status': 'done',
            'chunks': {
                'main': [
                    {
                        'name': 'main.js',
                        'path': '/static/main.js',
                    }
                ],
            },
        }
        self.webpack.state._load_stats = MagicMock()
        self.webpack.state._load_stats.return_value = self.stats

    def test_get_bundle(self):
        """ get_bundle() returns the chunks with a 'url' key added """
        bundle = self.webpack.get_bundle('main')
        self.assertEqual(bundle, self.stats['chunks']['main'])

    def test_filter_extensions(self):
        """ get_bundle() can filter by file extension """
        chunk = {
            'name': 'main.css',
            'path': '/static/main.css',
        }
        self.stats['chunks']['main'].append(chunk)
        bundle = self.webpack.get_bundle('main', '.css')
        self.assertEqual(bundle, [chunk])

    def test_filter_multiple_extensions(self):
        """ get_bundle() can filter by multiple file extensions """
        chunk = {
            'name': 'main.css',
            'path': '/static/main.css',
        }
        self.stats['chunks']['main'].append(chunk)
        bundle = self.webpack.get_bundle('main', '.js .css')
        self.assertEqual(bundle, self.stats['chunks']['main'])

    def test_filter_ignore(self):
        """ get_bundle() can ignore files by glob """
        chunk = {
            'name': 'main.css',
            'path': '/static/main.css',
        }
        self.stats['chunks']['main'].append(chunk)
        self.webpack.state.ignore = ['*.css']
        bundle = self.webpack.get_bundle('main')
        self.assertEqual(bundle, self.stats['chunks']['main'][:1])

    def test_filter_ignore_re(self):
        """ get_bundle() can ignore files by regular expression """
        chunk = {
            'name': 'main.css',
            'path': '/static/main.css',
        }
        self.stats['chunks']['main'].append(chunk)
        self.webpack.state.ignore_re = [re.compile(r'.*\.css')]
        bundle = self.webpack.get_bundle('main')
        self.assertEqual(bundle, self.stats['chunks']['main'][:1])

    def test_public_path(self):
        """ pulicPath in a chunk becomes the url """
        url = 'https://assets.cdn.com/main.js'
        self.stats['chunks']['main'][0]['publicPath'] = url
        bundle = self.webpack.get_bundle('main')
        self.assertEqual(bundle[0]['url'], url)

    def test_bad_bundle(self):
        """ Getting a nonexistant bundle raises an exception """
        with self.assertRaises(KeyError):
            self.webpack.get_bundle('nope')

    def test_error_status(self):
        """ If stats has error status, raise an error """
        self.stats['status'] = 'error'
        self.stats['error'] = 'FrobnicationError'
        self.stats['message'] = 'Retro quarks emitted during Frobnication'
        with self.assertRaises(RuntimeError):
            self.webpack.get_bundle('main')

    def test_bad_status(self):
        """ If stats has unknown status, raise an error """
        self.stats['status'] = 'wat'
        with self.assertRaises(RuntimeError):
            self.webpack.get_bundle('main')

    def test_missing_state(self):
        """ Raise an error if no WebpackState found """
        req = MagicMock()
        req.registry.webpack = {}
        with self.assertRaises(RuntimeError):
            Webpack(req)


def _get_bundle(request):
    """ Route view for the test webapp """
    config = request.matchdict['config']
    bundle_name = request.matchdict['bundle']
    bundle = request.webpack(config).get_bundle(bundle_name)
    renderer = request.params.get('renderer')
    if renderer:
        return render_to_response(renderer, {})
    else:
        return bundle


class TestWebapp(TempDirTest):
    """ Pyramid app tests """

    def setUp(self):
        super(TestWebapp, self).setUp()
        self.stats1 = {
            'status': 'done',
            'chunks': {
                'main': [
                    {
                        'name': 'main.js',
                        'path': '/static/main.js',
                    },
                ],
            },
        }
        self.stats2 = {
            'status': 'done',
            'chunks': {
                'libs': [
                    {
                        'name': 'libs.js',
                        'path': '/static/libs.js',
                    },
                ],
            },
        }

        settings = {
            'pyramid.includes': ['pyramid_jinja2', 'pyramid_webpack'],
            'jinja2.extensions': ['pyramid_webpack.jinja2ext:WebpackExtension'],
            'jinja2.directories': ['tests:templates/'],
            'webpack.debug': True,
            'webpack.stats_file': self._write('stats1.json', self.stats1),
            'webpack.configs': ['other'],
            'webpack.other.stats_file': self._write('stats2.json', self.stats2),
        }
        config = Configurator(settings=settings)

        config.add_route('bundle', '/bundle/{config}/{bundle}')
        config.add_view(_get_bundle, route_name='bundle', renderer='json')

        app = config.make_wsgi_app()
        self.app = webtest.TestApp(app)

    def tearDown(self):
        self.app.reset()

    def test_get_bundle(self):
        """ get_bundle() returns a list of all chunks in the bundle """
        res = self.app.get('/bundle/DEFAULT/main')
        bundle = json.loads(res.body.decode('utf-8'))
        expected = self.stats1['chunks']['main'][0]
        self.assertEqual(len(bundle), 1)
        self.assertEqual(bundle[0]['name'], expected['name'])
        self.assertEqual(bundle[0]['path'], expected['path'])
        self.assertTrue('url' in bundle[0])

    def test_get_second_bundle(self):
        """ get_bundle() works with the secondary webpack configs """
        res = self.app.get('/bundle/other/libs')
        bundle = json.loads(res.body.decode('utf-8'))
        expected = self.stats2['chunks']['libs'][0]
        self.assertEqual(len(bundle), 1)
        self.assertEqual(bundle[0]['name'], expected['name'])
        self.assertEqual(bundle[0]['path'], expected['path'])
        self.assertTrue('url' in bundle[0])

    def test_jinja2(self):
        """ The jinja2 extension can use 'webasset' blocks """
        res = self.app.get('/bundle/DEFAULT/main?renderer=paths.jinja2')
        expected = self.stats1['chunks']['main'][0]
        self.assertEqual(res.body.decode('utf-8'), expected['path'] + '\n')

    def test_jinja2_ext(self):
        """ The jinja2 extension can specify file extensions """
        res = self.app.get('/bundle/other/libs?renderer=paths2.jinja2')
        expected = self.stats2['chunks']['libs'][0]
        self.assertEqual(res.body.decode('utf-8'), expected['path'] + '\n')
