# -*- coding: utf-8 -*-
import os

import pytest
from hamcrest import (assert_that, has_entry, has_key, has_entries, is_, empty,
                      only_contains, contains_inanyorder, contains)

from confight import parse, merge, find, load, load_paths, load_app, FORMATS


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

    def test_it_should_load_existing_files(self, examples):
        path = examples.get(FILES[0])

        found = find(path)

        assert_that(found, contains(path))

    def test_it_should_normalize_relative_paths(self):
        path = os.path.join('.', os.path.basename(__file__))

        found = find(path)

        assert_that(found, contains(__file__))

    def test_it_should_return_nothing_for_missing_directories(self):
        assert_that(find('/path/to/nowhere'), is_(empty()))


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


class TestLoadApp(object):
    def test_it_should_load_from_default_path(self):
        def myparser(path, format=None):
            return {path: True}

        def myfinder(path):
            return [path]

        config = load_app('myapp', parser=myparser, finder=myfinder)

        assert_that(list(config), contains_inanyorder(
            '/etc/myapp/config.toml', '/etc/myapp/conf.d',
        ))

    def test_it_should_load_extra_paths(self):
        def myparser(path, format=None):
            return {path: True}

        def myfinder(path):
            return [path]

        config = load_app('myapp', paths=['/extra/path'],
                          parser=myparser, finder=myfinder)

        assert_that(list(config), contains_inanyorder(
            '/etc/myapp/config.toml', '/etc/myapp/conf.d', '/extra/path'
        ))


class Repository(object):
    def __init__(self, tmpdir):
        self.tmpdir = tmpdir

    def get(self, name):
        if name not in self._files:
            self._files[name] = self.load(name)
        return self._files[name]

    def get_many(self, names):
        return [self.get(name) for name in names]

    def clear(self):
        self._files.clear()

    def load(self, name):
        fileobj = self.tmpdir.join(name)
        fileobj.write(self._contents[name].encode('utf8'), 'wb')
        return str(fileobj)

    _files = {}
    _contents = {
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
    null: null
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
