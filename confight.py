import io
import os
import glob
import json
import logging
import itertools
try:
    from ConfigParser import ConfigParser
except ImportError:
    from configparser import ConfigParser

import toml

logger = logging.getLogger('confight')


def load_user_app(name, **kwargs):
    """Parse and merge app and user config from default locations

    User config will take precedence.

    :param name: Name of the application to load
    :returns: Single dict with all the loaded config
    """
    kwargs.setdefault(
        'user_file_path', os.path.join('~/.config/', name, 'config.toml'))
    kwargs.setdefault(
        'user_dir_path', os.path.join('~/.config/', name, 'conf.d'))
    return load_app(name, **kwargs)


def load_app(name, **kwargs):
    """Parse and merge app config from default locations

    :param name: Name of the application to load
    :returns: Single dict with all the loaded config
    """
    kwargs.setdefault('file_path', os.path.join('/etc', name, 'config.toml'))
    kwargs.setdefault('dir_path', os.path.join('/etc', name, 'conf.d'))
    return load_app_paths(**kwargs)


def load_app_paths(file_path=None, dir_path=None,
                   user_file_path=None, user_dir_path=None, **kwargs):
    """Parse and merge user and app config files

    User config will have precedence

    :param file_path: Path to the base config file
    :param dir_path: Path to the extension config directory
    :param user_file_path: Path to the user base config file
    :param user_dir_path: Path to the user base config file
    :returns: Single dict with all the loaded config
    """
    paths = [file_path, dir_path, user_file_path, user_dir_path]
    return load_paths([path for path in paths if path], **kwargs)


def load_paths(paths, finder=None, **kwargs):
    """Parse and merge config in path and directories

    :param finder: Finder function(dir_path) returning ordered list of paths
    :returns: Single dict with all the loaded config
    """
    finder = find if finder is None else finder
    files = itertools.chain.from_iterable(finder(path) for path in paths)
    return load(files, **kwargs)


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


def parse(path, format=None):
    """Parse the config file at the given path

    :param path: Path to the config file
    :param format: Name of the format (default: guess from file extension)
    :returns: dict with the parsed contents
    """
    format = format_from_path(path) if format is None else format
    logger.info('Parsing %r config file from %r', format, path)
    if format not in FORMATS:
        raise ValueError('Unknown format {} for file {}'.format(format, path))
    loader = FORMAT_LOADERS[format]
    with io.open(path, 'r', encoding='utf8') as stream:
        return loader(stream)


def merge(configs):
    """Merge list of dicts into a single one

    For the same key, the last appearing value will prevail.
    When value for a key is a dict, will merged recursively.
    Merging dicts with other values will take dicts and ignore the rest.

    :param configs: List of parsed config dicts in order
    :returns: dict with the merged resulting config
    """
    logger.debug('Merging config data %r', configs)
    result = {}
    for key in set(key for config in configs for key in config):
        values = [config[key] for config in configs if key in config]
        merges = [v for v in values if isinstance(v, dict)]
        result[key] = merge(merges) if merges else values[-1]
    return result


def find(path):
    """Find files in the filesystem in order

    Expands and normalizes relative paths.
    Ignores unreadable files and unexplorable directories.

    :param dir_path: Path to a config file or dir containing configs
    :returns: List of full paths of the files in the directory in lex. order
    """
    if not check_access(path):
        return []
    path = os.path.abspath(os.path.expanduser(path))
    if os.path.isfile(path):
        return [path]
    return sorted(glob.glob(os.path.join(path, '*')))


def check_access(path):
    """Return whether a config file or directory can be read"""
    if not path:
        return False
    elif not os.access(path, os.R_OK):
        logger.error('Could not read %r', path)
        return False
    elif os.path.isdir(path) and not os.access(path, os.X_OK):
        logger.error('Could not list directory %r', path)
        return False
    elif os.access(path, os.X_OK):
        logger.warning('Config file %r has exec permissions', path)
    return True


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
