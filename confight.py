from __future__ import print_function

import argparse
import glob
import io
import itertools
import json
import logging
import os
import sys
from collections import OrderedDict
from configparser import ConfigParser, ExtendedInterpolation
from logging import Logger
from typing import IO, Any, Callable, Dict, List, Optional, Set

import toml

__version__: str = "2.0.0-2"
logger: Logger = logging.getLogger("confight")


TConfigurationData = Dict[str, Any]
TFormatLoader = Callable[[IO, str], TConfigurationData]
TParser = Callable[[str, Optional[str]], TConfigurationData]
TMerger = Callable[[List[TConfigurationData]], TConfigurationData]


def load_user_app(
    name: str, extension: str = "toml", user_prefix: Optional[str] = None, **kwargs
) -> TConfigurationData:
    """Parse and merge app and user config from default locations

    User config will take precedence.

    :param name: Name of the application to load
    :param extension: filename extension for config, defaults to `toml`
    :param force_extension: Only read files with given extension.
    :param user_prefix: base directory for default user config locations
                        defaults to ~/.config/<name>
    :returns: Single dict with all the loaded config
    """
    if user_prefix is None:
        user_prefix = os.path.join("~/.config", name)
    filename = "config.{ext}".format(ext=extension)
    kwargs.setdefault("user_file_path", os.path.join(user_prefix, filename))
    kwargs.setdefault("user_dir_path", os.path.join(user_prefix, "conf.d"))
    return load_app(name, extension, **kwargs)


def load_app(
    name: str, extension: str = "toml", prefix: Optional[str] = None, **kwargs
) -> TConfigurationData:
    """Parse and merge app config from default locations

    :param name: Name of the application to load
    :param extension: filename extension for config, defaults to `toml`
    :param prefix: base directory for default config locations,
                   defaults to `/etc/<name>`
    :param force_extension: Only read files with given extension.
    :returns: Single dict with all the loaded config
    """
    if prefix is None:
        prefix = os.path.join("/etc", name)
    filename = "config.{ext}".format(ext=extension)
    kwargs.setdefault("file_path", os.path.join(prefix, filename))
    kwargs.setdefault("dir_path", os.path.join(prefix, "conf.d"))
    return load_app_paths(extension=extension, **kwargs)


def load_app_paths(
    file_path: Optional[str] = None,
    dir_path: Optional[str] = None,
    user_file_path: Optional[str] = None,
    user_dir_path: Optional[str] = None,
    default: Optional[str] = None,
    paths: Optional[str] = None,
    **kwargs
) -> TConfigurationData:
    """Parse and merge user and app config files

    User config will have precedence

    :param file_path: Path to the base config file
    :param dir_path: Path to the extension config directory
    :param user_file_path: Path to the user base config file
    :param user_dir_path: Path to the user base config file
    :param default: Path to be prepended as the default config file embedded
                    in the app
    :param paths: Extra paths to add to the parsing after the defaults
    :param force_extension: only read files with given extension.
    :returns: Single dict with all the loaded config
    """
    files = [default, file_path, dir_path, user_file_path, user_dir_path]
    files += paths or []
    return load_paths([path for path in files if path], **kwargs)


def load_paths(
    paths: List[str],
    finder: Optional[Callable[[str], List[str]]] = None,
    extension: Optional[str] = None,
    force_extension: bool = False,
    **kwargs
) -> TConfigurationData:
    """Parse and merge config in path and directories

    :param paths: List of files to parse
    :param finder: Finder function(dir_path) returning ordered list of paths
    :param extension: Extension of the files to filter
    :param force_extension: Only read files with given extension.
    :returns: Single dict with all the loaded config
    """
    finder = find if finder is None else finder
    files = list(itertools.chain.from_iterable(finder(path) for path in paths))
    if extension and force_extension:
        files = [path for path in files if path.endswith("." + extension)]
    return load(files, **kwargs)


def load(
    paths: List[str],
    format: Optional[str] = None,
    parser: Optional[TParser] = None,
    merger: Optional[TMerger] = None,
) -> TConfigurationData:
    """Parse and merge a list of configuration files

    :param paths: List of files to parse
    :param format: Format for the files to load (default: guess from extension)
    :param parser: Parse function(path, format=None) returning a dict
    :param merger: Merge function(list_of_dicts) returning a dict
    :returns: Single dict with all the loaded config
    """
    # NOTE: Mypy bug
    # error: Incompatible types in assignment (expression has type "function", variable has type "Callable[[str, Optional[str]], Dict[str, Any]]")
    # https://github.com/python/mypy/issues/16868
    the_parser: TParser = parse if parser is None else parser  # type: ignore
    the_merger: TMerger = merge if merger is None else merger
    return the_merger([the_parser(path, format) for path in paths])


def parse(path: str, format: Optional[str] = None) -> TConfigurationData:
    """Parse the config file at the given path

    :param path: Path to the config file
    :param format: Name of the format (default: guess from file extension)
    :returns: dict with the parsed contents
    """
    the_format: str = format_from_path(path) if format is None else format
    logger.info("Parsing %r config file from %r", the_format, path)
    if the_format not in FORMATS:
        raise ValueError("Unknown format {} for file {}".format(the_format, path))
    loader: TFormatLoader = FORMAT_LOADERS[the_format]
    with io.open(path, "r", encoding="utf8") as stream:
        return loader(stream, the_format)


def merge(configs: List[TConfigurationData]) -> TConfigurationData:
    """Merge list of dicts into a single dict

    For the same key, the last appearing value will prevail.
    When value for a key is a dict, it will merged recursively.
    Merging dicts with other types will take the dict and ignore the other.

    :param configs: List of parsed config dicts in order
    :returns: dict with the merged resulting config
    """
    logger.debug("Merging config data %r", configs)
    result = OrderedDict()
    # No OrderedSets available
    keys = OrderedDict((key, None) for config in configs for key in config)
    for key in keys:
        values = [config[key] for config in configs if key in config]
        merges = [v for v in values if isinstance(v, dict)]
        result[key] = merge(merges) if merges else values[-1]
    return result


def find(path: str) -> List[str]:
    """Find files in the filesystem in order

    Expands and normalizes relative paths.
    Ignores unreadable files and unexplorable directories.

    :param dir_path: Path to a config file or dir containing configs
    :returns: List of full paths of the files in the directory in lex. order
    """
    if path:
        path = os.path.abspath(os.path.expanduser(path))
    if not check_access(path):
        return []
    if os.path.isfile(path):
        return [path]
    return sorted(glob.glob(os.path.join(path, "*")))


def check_access(path: str) -> bool:
    """Return whether a config file or directory can be read"""
    if not path:
        return False
    elif not os.path.exists(path):
        logger.debug("Could not find %r", path)
        return False
    elif not os.access(path, os.R_OK):
        logger.error("Could not read %r", path)
        return False
    elif os.path.isdir(path) and not os.access(path, os.X_OK):
        logger.error("Could not list directory %r", path)
        return False
    elif os.path.isfile(path) and os.access(path, os.X_OK):
        logger.warning("Config file %r has exec permissions", path)
    return True


def load_json(stream: IO, format: Optional[str] = None) -> TConfigurationData:
    return json.load(stream, object_pairs_hook=OrderedDict)


def load_toml(stream: IO, format: Optional[str] = None) -> TConfigurationData:
    return toml.load(stream, _dict=OrderedDict)


def load_ini(stream: IO, format: Optional[str] = None) -> TConfigurationData:
    if "ExtendedInterpolation" in globals():
        parser = ConfigParser(interpolation=ExtendedInterpolation())
    else:
        parser = ConfigParser()
    parser.read_file(stream)
    return {section: OrderedDict(parser.items(section)) for section in parser.sections()}


FORMATS: Set[str] = {"toml", "ini", "json"}
FORMAT_EXTENSIONS: Dict[str, str] = {
    "js": "json",
    "json": "json",
    "toml": "toml",
    "ini": "ini",
    "cfg": "ini",
}
FORMAT_LOADERS: Dict[str, TFormatLoader] = {
    "json": load_json,
    "toml": load_toml,
    "ini": load_ini,
}


# Optional dependency yaml
try:
    from ruamel.yaml import YAML  # type: ignore
except ImportError:
    pass
else:

    def load_yaml(stream: IO, format: Optional[str] = None) -> TConfigurationData:
        yaml = YAML(typ="rt")
        return yaml.load(stream)

    FORMATS.add("yaml")
    FORMAT_EXTENSIONS.update({"yml": "yaml", "yaml": "yaml"})
    FORMAT_LOADERS.update({"yaml": load_yaml})

# Optional dependency HCL
try:
    import hcl  # type: ignore
except ImportError:
    pass
else:

    def load_hcl(stream: IO, format: Optional[str] = None) -> TConfigurationData:
        return hcl.load(stream)

    FORMATS.add("hcl")
    FORMAT_EXTENSIONS.update({"hcl": "hcl"})
    FORMAT_LOADERS.update({"hcl": load_hcl})


def format_from_path(path: str) -> str:
    """Get file format from a given path based on extension"""
    ext = os.path.splitext(path)[1][1:]  # extension without dot
    format = FORMAT_EXTENSIONS.get(ext)
    if not format:
        raise ValueError("Unknown format extension {!r} for {!r}".format(ext, path))
    return format


def get_version() -> str:
    import pkg_resources

    return "confight " + pkg_resources.get_distribution("confight").version


def cli_configure_logging(args):
    logger.setLevel(args.verbose)
    logger.addHandler(logging.StreamHandler())


def cli_show(args):
    """Load config and show it"""
    config = load_user_app(args.name, prefix=args.prefix, user_prefix=args.user_prefix)
    print(toml.dumps(config), end="")


def cli():
    LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    parser = argparse.ArgumentParser(description="One simple way of parsing configs")
    parser.add_argument("--version", action="version", version=get_version())
    parser.add_argument(
        "-v", "--verbose", choices=LOG_LEVELS, default="ERROR", help="Logging level default: ERROR"
    )
    subparsers = parser.add_subparsers(title="subcommands", dest="command")
    show_parser = subparsers.add_parser("show")
    show_parser.add_argument("name", help="Name of the application")
    show_parser.add_argument("--prefix", help="Base for default paths")
    show_parser.add_argument("--user-prefix", help="Base for default user paths")

    args = parser.parse_args()
    cli_configure_logging(args)
    # Use callbacks, parser.set_defaults(func=) does not work in Python3.3
    callbacks = {
        "show": cli_show,
        None: lambda args: parser.print_help(file=sys.stderr),
    }
    try:
        callbacks[args.command](args)
    except Exception as error:
        log = logger.exception if args.verbose == "DEBUG" else logger.error
        log("Error: %s", error)
        sys.exit(1)
