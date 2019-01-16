# -*- coding: utf-8 -*-
import os
try:
    import subprocess32 as subprocess
except ImportError:
    import subprocess
try:
    import mock
except ImportError:
    from unittest import mock

import pytest
from hamcrest import (assert_that, has_entry, has_key, has_entries, is_, empty,
                      only_contains, contains, contains_string)

from confight import (parse, merge, find, load, load_paths, load_app,
                      load_user_app, FORMATS)


@pytest.fixture
def examples(tmpdir):
    return Repository(tmpdir)


FILES = [
    'basic_file.toml', 'basic_file.ini', 'basic_file.json', 'basic_file.cfg',
    'basic_file.js'
]
if "yaml" in FORMATS:
    FILES.extend(["basic_file.yaml", "basic_file.yml"])

INVALID_FILES = [
    'invalid.toml', 'invalid.ini', 'invalid.json', 'invalid.cfg', 'invalid.js'
]
INVALID_EXTENSIONS = ['bad_ext.ext', 'bad_ext.j']
SORTED_FILES = ['00_base.toml', '01_first.json', 'AA_second.ini']


class TestParse(object):
    @pytest.mark.parametrize("name", FILES)
    def test_it_should_detect_format_from_extension(self, name, examples):
        config = parse(examples.get(name))

        assert_that(config, has_entry('section', has_key('string')))

    @pytest.mark.parametrize("name", FILES)
    def test_it_loads_strings_as_unicode(self, name, examples):
        config = parse(examples.get(name))

        assert_that(config, has_entry(
            'section', has_entry('unicode', is_(u'💩'))
        ))

    @pytest.mark.parametrize("name, format", [
        ('basic_file_toml', 'toml'),
        ('basic_file_ini', 'ini'),
        ('basic_file_json', 'json'),
    ])
    def test_it_should_load_for_given_format(self, name, format, examples):
        config = parse(examples.get(name), format)

        assert_that(config, has_entry('section', has_key('string')))

    def test_it_should_fail_with_missing_files(self):
        with pytest.raises(Exception):
            parse('/path/to/nowhere.json')

    @pytest.mark.parametrize("name", INVALID_FILES)
    def test_it_should_fail_with_invalid_files(self, name, examples):
        with pytest.raises(Exception):
            parse(examples.get(name))

    @pytest.mark.parametrize("name", INVALID_EXTENSIONS)
    def test_it_should_fail_with_invalid_extensions(self, name, examples):
        with pytest.raises(Exception):
            parse(examples.get(name))


class TestMerge(object):
    def test_it_should_give_priority_to_last_value(self):
        configs = [
            {'key': 1},
            {'key': 2},
            {'key': 3},
        ]

        result = merge(configs)

        assert_that(result, has_entry('key', 3))

    def test_it_should_add_all_values(self):
        configs = [
            {'section1': {'key1': 1}},
            {'section2': {'key2': 2}},
            {'section3': {'key3': 3}},
        ]

        result = merge(configs)

        assert_that(result, has_entries({
            'section1': has_entry('key1', 1),
            'section2': has_entry('key2', 2),
            'section3': has_entry('key3', 3),
        }))

    def test_it_should_merge_dicts_recursively(self):
        configs = [
            {'section': {'lv1': {'lv2': {'lv3': 1}}}},
            {'section': {'lv1': {'lv2': {'lv3': 2}}}},
            {'section': {'lv1': {'lv2': {'lv3': 3}}}},
        ]

        result = merge(configs)

        assert_that(result, has_entry(
            'section', has_entry(
                'lv1', has_entry(
                    'lv2', has_entry(
                        'lv3', 3)))
        ))

    def test_it_should_ignore_scalar_values_given_as_configs(self):
        configs = [
            {'section': {'key': 1}},
            {'section': None},
            {'section': {'key': 2}},
            {'section': []},
            {'section': {'key': 3}},
        ]

        result = merge(configs)

        assert_that(result, has_entry('section', has_entry('key', 3)))


class TestFind(object):
    def test_it_should_load_files_in_order(self, examples):
        examples.clear()
        expected_files = sorted(examples.get_many(SORTED_FILES))

        found = find(str(examples.tmpdir))

        assert_that(found, is_(expected_files))

    def test_it_should_load_full_paths(self, examples):
        examples.clear()
        examples.get_many(SORTED_FILES)

        found = find(str(examples.tmpdir))

        assert_that(
            all(os.path.isabs(path) for path in found),
            is_(True)
        )

    def test_it_should_normalize_relative_paths(self):
        path = os.path.join('.', os.path.basename(__file__))

        found = find(path)

        assert_that(found, contains(__file__))

    def test_it_should_load_existing_files(self, examples):
        path = examples.get(FILES[0])

        found = find(path)

        assert_that(found, contains(path))

    def test_it_should_return_nothing_for_missing_directories(self):
        assert_that(find('/path/to/nowhere'), is_(empty()))

    def test_it_should_ignore_invalid_files(self):
        found = find(None)

        assert_that(found, is_(empty()))

    def test_it_should_ignore_unreadable_files(self, examples):
        unreadable_path = examples.load(FILES[0])
        os.chmod(unreadable_path, 0o222)

        found = find(unreadable_path)

        assert_that(found, is_(empty()))

    def test_it_should_ignore_unexplorable_dirs(self, tmpdir):
        unexplorable_dir = str(tmpdir)
        os.chmod(unexplorable_dir, 0o444)

        found = find(unexplorable_dir)

        assert_that(found, is_(empty()))

    @mock.patch('confight.logger')
    def test_it_should_warn_about_executable_config_files(self, logger, examples):
        executable_file = examples.load(FILES[0])
        os.chmod(executable_file, 0o777)

        found = find(executable_file)

        assert_that(found, contains(executable_file))
        logger.warning.assert_called()


class TestLoad(object):
    def test_it_should_load_and_merge_lists_of_paths(self, examples):
        paths = sorted(examples.get_many(SORTED_FILES))

        config = load(paths)

        assert_that(config, has_entry('section', has_entry('key', 'second')))

    def test_it_should_load_paths_for_given_format(self, examples):
        paths = examples.get_many(['00_base.toml', 'basic_file_toml'])

        config = load(paths, format='toml')

        assert_that(config, has_entry('section', has_entry('key', 'basic')))

    def test_it_should_use_given_parser(self):
        paths = ['/path/to/1', '/path/to/2']

        def myparse(path, format=None):
            return {'path': path, 'format': format}

        config = load(paths, format='toml', parser=myparse)

        assert_that(config, has_entries({
            'path': paths[-1],
            'format': 'toml'
        }))

    def test_it_should_use_given_merger(self, examples):
        paths = examples.get_many(SORTED_FILES)

        def mymerge(configs):
            return configs

        config = load(paths, merger=mymerge)

        assert_that(config, only_contains(has_key('section')))


class TestLoadPaths(object):
    def test_it_should_load_from_file_and_directory(self, examples):
        examples.clear()
        paths = sorted(examples.get_many(SORTED_FILES))

        config = load_paths([paths[0], str(examples.tmpdir)])

        assert_that(config, has_entry('section', has_entry('key', 'second')))

    def test_merges_must_retain_order(self, examples):
        examples.clear()
        paths = examples.get_many(FILES)

        config = load(paths)

        good_data = [
            'string', 'integer', 'float', 'boolean', 'list', 'key', 'unicode',
            'subsection', 'null'
        ]

        assert_that(config["section"].keys(), contains(*good_data))


class LoadAppBehaviour(object):
    def loaded_paths(self, config):
        return sorted(config, key=lambda k: config[k])

    def call_config_loader(self, loader, *args, **kwargs):
        """Simulate config loading

        Result is a dictionary with all loaded d[key, int] with every
        loaded path the order in which they were loaded.
        """
        def myparser(path, format=None, _data={'n': 0}):
            _data['n'] += 1
            return {path: _data['n']}

        def myfinder(path):
            return [path]

        kwargs.setdefault('parser', myparser)
        kwargs.setdefault('finder', myfinder)
        return loader(*args, **kwargs)


class TestLoadApp(LoadAppBehaviour):
    def test_it_should_load_from_default_path(self):
        config = self.load_app('myapp')

        assert_that(self.loaded_paths(config), contains(
            '/etc/myapp/config.toml', '/etc/myapp/conf.d',
        ))

    def test_it_should_load_extra_paths(self):
        config = self.load_app('myapp', paths=['/extra/path'])

        assert_that(self.loaded_paths(config), contains(
            '/etc/myapp/config.toml', '/etc/myapp/conf.d', '/extra/path'
        ))

    def test_it_should_allow_using_known_extensions(self):
        config = self.load_app('myapp', extension='json')

        assert_that(self.loaded_paths(config), contains(
            '/etc/myapp/config.json', '/etc/myapp/conf.d',
        ))

    def test_it_should_reject_custom_extensions(self):
        with pytest.raises(ValueError):
            self.load_app('myapp', extension='jsn', parser=parse)

    def test_it_should_allow_using_custom_extensions_with_format(self):
        config = self.load_app('myapp', extension='jsn', format='json')

        assert_that(self.loaded_paths(config), contains(
            '/etc/myapp/config.jsn', '/etc/myapp/conf.d',
        ))

    def test_it_should_use_prefix_for_default_locations(self):
        config = self.load_app('myapp', prefix='/my/path')

        assert_that(self.loaded_paths(config), contains(
            '/my/path/config.toml', '/my/path/conf.d',
        ))

    def load_app(self, *args, **kwargs):
        return self.call_config_loader(load_app, *args, **kwargs)


class TestLoadUserApp(LoadAppBehaviour):
    def test_it_should_load_from_default_user_path(self):
        config = self.load_app('myapp')

        assert_that(self.loaded_paths(config), contains(
            '/etc/myapp/config.toml',
            '/etc/myapp/conf.d',
            '~/.config/myapp/config.toml',
            '~/.config/myapp/conf.d'
        ))

    def test_it_should_load_extra_paths(self):
        config = self.load_app('myapp', paths=['/extra/path'])

        assert_that(self.loaded_paths(config), contains(
            '/etc/myapp/config.toml',
            '/etc/myapp/conf.d',
            '~/.config/myapp/config.toml',
            '~/.config/myapp/conf.d',
            '/extra/path'
        ))

    def test_it_should_allow_using_known_extensions(self):
        config = self.load_app('myapp', extension='json')

        assert_that(self.loaded_paths(config), contains(
            '/etc/myapp/config.json',
            '/etc/myapp/conf.d',
            '~/.config/myapp/config.json',
            '~/.config/myapp/conf.d',
        ))

    def test_it_should_reject_custom_extensions(self):
        with pytest.raises(ValueError):
            self.load_app('myapp', extension='jsn', parser=parse)

    def test_it_should_allow_using_custom_extensions_with_format(self):
        config = self.load_app('myapp', extension='jsn', format='json')

        assert_that(self.loaded_paths(config), contains(
            '/etc/myapp/config.jsn',
            '/etc/myapp/conf.d',
            '~/.config/myapp/config.jsn',
            '~/.config/myapp/conf.d',
        ))

    def test_it_should_use_prefix_for_default_locations(self):
        config = self.load_app('myapp', prefix='/my/path')

        assert_that(self.loaded_paths(config), contains(
            '/my/path/config.toml',
            '/my/path/conf.d',
            '~/.config/myapp/config.toml',
            '~/.config/myapp/conf.d',
        ))

    def test_it_should_use_prefix_for_default_user_locations(self):
        config = self.load_app('myapp', user_prefix='/my/path')

        assert_that(self.loaded_paths(config), contains(
            '/etc/myapp/config.toml',
            '/etc/myapp/conf.d',
            '/my/path/config.toml',
            '/my/path/conf.d',
        ))

    def load_app(self, *args, **kwargs):
        return self.call_config_loader(load_user_app, *args, **kwargs)


class TestCli(object):
    def test_it_should_print_help(self):
        out = subprocess.run([self.bin], stderr=subprocess.PIPE)

        assert_that(out.stderr.decode('utf8'), contains_string('usage:'))

    def test_it_should_show_message_on_exit(self, examples):
        examples.clear()
        examples.create('config.toml', b'[broken')

        out = self.run(['show', 'name', '--prefix', str(examples.tmpdir)])

        assert_that(out.stderr.decode('utf8'), contains_string('Error:'))
        assert_that(out.returncode, is_(1))

    def test_it_should_show_config(self, examples):
        examples.clear()
        examples.get('config.toml')
        contents = examples.get_contents('config.toml')

        out = self.run(['show', 'name', '--prefix', str(examples.tmpdir)])

        assert_that(out.stdout.decode('utf8'), is_(contents))
        assert_that(out.returncode, is_(0))

    def run(self, args):
        return subprocess.run(
            [self.bin] + list(args),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

    @property
    def bin(self):
        name = 'confight'
        prefix = os.getenv('VIRTUAL_ENV', '')
        if prefix:
            name = os.path.join(prefix, 'bin', name)
        return name


# Evil monkeypatching for python 3.3 and python 3.4
if getattr(subprocess, 'run', None) is None:
    class CompletedProcess:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    def maimed_run(*args, **kwargs):
        with subprocess.Popen(*args, **kwargs) as process:
            try:
                stdout, stderr = process.communicate()
            except:  # noqa
                process.kill()
                process.wait()
                raise
            retcode = process.poll()

        return CompletedProcess(
            args=process.args,
            returncode=retcode,
            stdout=stdout,
            stderr=stderr
        )

    subprocess.run = maimed_run


class Repository(object):
    def __init__(self, tmpdir):
        self.tmpdir = tmpdir

    def get(self, name):
        if name not in self._files:
            self._files[name] = self.load(name)
        return self._files[name]

    def get_many(self, names):
        return [self.get(name) for name in names]

    def get_contents(self, name):
        return self._contents[name]

    def clear(self):
        self._files.clear()

    def create(self, name, contents):
        fileobj = self.tmpdir.join(name)
        fileobj.write(contents, 'wb')
        return str(fileobj)

    def load(self, name):
        return self.create(name, self._contents[name].encode('utf8'))

    _files = {}
    _contents = {
        'config.toml': u"""\
[section]
string = "toml"
""",
        'basic_file.toml': u"""
# Basic toml file
[section]
string = "toml"
integer = 1
float = 1.5
boolean = true
list = ["first", "second"]
key = "basic"
unicode = "💩"

[section.subsection]
key = "value"
""",
        'basic_file.ini': u"""
# Basic ini file
[section]
string = string
unicode = 💩
""",
        'basic_file.json': u"""
{
  "section": {
    "string": "json",
    "integer": 3,
    "float": 3.5,
    "boolean": false,
    "null": null,
    "list": ["third", "fourth"],
    "unicode": "💩"
  }
}
""",
        'basic_file.yaml': u"""
section:
    string: "json"
    integer: 3
    float: 3.5
    boolean: false
    "null": null
    list:
        - third
        - fourth
    unicode: "💩"
""",
        'invalid.toml': """
[section]
key = null
""",
        'invalid.ini': """
=
""",
        'invalid.json': """
{"invalid"}
""",
        '00_base.toml': """
[section]
key = "zero"
""",
        '01_first.json': """
{
  "section": {
    "key": "first"
  }
}
""",
        'AA_second.ini': """
[section]
key = second
""",
    }
    _contents['basic_file_toml'] = _contents['basic_file.toml']
    _contents['basic_file_ini'] = _contents['basic_file.ini']
    _contents['basic_file_json'] = _contents['basic_file.json']
    _contents['basic_file.js'] = _contents['basic_file.json']
    _contents['basic_file.cfg'] = _contents['basic_file.ini']
    _contents['invalid.js'] = _contents['invalid.json']
    _contents['invalid.cfg'] = _contents['invalid.ini']
    _contents['bad_ext.ext'] = _contents['basic_file.toml']
    _contents['bad_ext.j'] = _contents['basic_file.json']
    _contents['bad_ext.u'] = _contents['basic_file.yaml']
    _contents['basic_file_yaml'] = _contents['basic_file.yaml']
    _contents['basic_file.yml'] = _contents['basic_file.yaml']
