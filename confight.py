import io
import os
import glob
import json
try:
    from ConfigParser import ConfigParser
except ImportError:
    from configparser import ConfigParser

import toml


def load(paths, format=None, parser=None, merger=None):
    """Parse and merge a list of configuration files

    :param paths: List of files to parse
    :param format: Format for the files to load (default: guess from extension)
    :param parser: Parse function(path, format=None) returning a dict
    :param merger: Merge function(list_of_dicts) returning a dict
    :returns: Single dict with all the loaded config
    """
    parser = parse if parser is None else parser
    merger = merge if merger is None else merger
    return merger([parser(path, format=format) for path in paths])


def load_paths(file_path, dir_path, finder=None, **kwargs):
    """Parse and merge config in path and directories

    :param file_path: Path to the base config file
    :param dir_path: Path to the extension config directory
    :param finder: Finder function(dir_path) returning ordered list of paths
    :returns: Single dict with all the loaded config
    """
    finder = find if finder is None else finder
    return load([file_path] + finder(dir_path), **kwargs)


def load_app(name, **kwargs):
    """Parse and merge config from default location

    :param name: Name of the application to load
    :returns: Single dict with all the loaded config
    """
    kwargs.setdefault('file_path', os.path.join('/etc', name, 'config.toml'))
    kwargs.setdefault('dir_path', os.path.join('/etc', name, 'conf.d'))
    return load_paths(**kwargs)


def load_ini(stream):
    parser = ConfigParser()
    parser.readfp(stream)
    return {
        section: dict(parser.items(section))
        for section in parser.sections()
    }


FORMATS = ('toml', 'ini', 'json')
FORMAT_EXTENSIONS = {
    'js': 'json',
    'json': 'json',
    'toml': 'toml',
    'ini': 'ini',
    'cfg': 'ini',
}
FORMAT_LOADERS = {
    'json': json.load,
    'toml': toml.load,
    'ini': load_ini
}


def format_from_path(path):
    """Get file format from a given path based on exension"""
    ext = os.path.splitext(path)[1][1:]  # extension without dot
    format = FORMAT_EXTENSIONS.get(ext)
    if not format:
        raise ValueError(
            'Unknown format extension {!r} for {!r}'.format(ext, path)
        )
    return format


def parse(path, format=None):
    """Parse the config file at the given path

    :param path: Path to the config file
    :param format: Name of the format (default: guess from file extension)
    :returns: dict with the parsed contents
    """
    format = format_from_path(path) if format is None else format
    if format not in FORMATS:
        raise ValueError('Unknown format {} for file {}'.format(format, path))
    loader = FORMAT_LOADERS[format]
    with io.open(path, 'r', encoding='utf8') as stream:
        return loader(stream)


def merge(configs):
    """Merge several config files in order

    :param configs: List of config files in order
    :returns: dict with the merged resulting config
    """
    result = {}
    for key in set(key for config in configs for key in config):
        values = [config[key] for config in configs if key in config]
        merges = [v for v in values if isinstance(v, dict)]
        result[key] = merge(merges) if merges else values[-1]
    return result


def find(dir_path):
    """Find files in the filesystem in order

    :param dir_path: Path to a directory containing configs
    :returns: Full paths to the files in the directory in lex. order
    """
    return sorted(glob.glob(os.path.join(dir_path, '*')))
