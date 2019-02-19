confight
========

[![PyPI](https://img.shields.io/pypi/v/confight.svg)](https://pypi.org/project/confight/)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/confight.svg)
[![Build Status](https://travis-ci.org/Avature/confight.svg?branch=master)](https://travis-ci.org/Avature/confight)

One simple way of parsing configs

- Extensible "*Unix-like*" `conf.d` directory
- Allow for multiple formats (*toml*, *json*, *yaml*, *ini*)
- Full unicode support
- User settings `~/.config` support
- Nice out-of-the-box defaults
- See [examples](#examples)

**confight** focuses on making application configuration easy to load, change,
extend, generate and audit. It does so by allowing to use separated files for
different topics, simplifying changes and new additions, without messing with
already existing defaults or deleting or moving protected files.

This is achieved by using at least one config file (`/etc/app/config.toml`)
and an extra directory (`/etc/app/conf.d`) for extra files.

Those extra files are called *droplets* which consist in is a small config
file that is *"dropped"* into a `conf.d` directory where they will be parsed
and merged nicely into a single final configuration.

The idea is to "*map reduce*" configurations, by parsing all files *in order*,
giving more relevance to the latest appearance and then merge them into a
*single config* that holds all the data:

```
 C₀ -- parse -----|
    C₁ -- parse --|
    C₂ -- parse --|-- merge --> C
       ⋮          |
    Cₙ -- parse --|
```

The name of those files will determine the order in which they're parsed and
the priority their values will have when merging. The last one wins.

This approach is very common in Unix and used in cron (`/etc/cron.d`), bash
profiles (`/etc/profile.d`), apt (`/etc/apt/sources.list.d`), systemd and many
others. Is specially good for externally managed configs or *debian-packaged*
applications, avoiding clashes between installed files and generated configs,
avoiding changes that would stay forever unless manually merged (Yes, I've
said 💩MANUALLY💩💩Placing new files in `conf.d`, application configuration
can change be extended and overriden without getting dirty.

## Usage

```python
>>> import confight
>>> confight.load_app('myapp')
{
    "section": {
        "key": "value"
    }
}
```

The previous fragment got all the config files at `/etc/myapp/config.toml` and
within the `/etc/myapp/conf.d` directory and merged them into a single config.

```
# /etc/myapp/config.toml    /etc/myapp/conf.d/00_first.json    /etc/myapp/conf.d/99_second.ini
[section]                   {                                  [section]
key = "base config"           "section": {                     key = value
                                 "key": "not this"
                              }
                            }
```

Default file locations for an application named `myapp` would be at:

- `/etc/myapp/config.toml`
- `/etc/myapp/conf.d/*`

User custom configurations would be read (if any) from:

- `~/.config/myapp/config.toml`
- `~/.config/myapp/conf.d/*`

See the [examples](#examples) section for more information on how to use these
functions.

## Loading

The `load` family of functions take a list of names, files or directories to
easily parse and merge a related set of configurations:

```python
confight.load_app('myapp')
confight.load_user_app('myapp')
confight.load_paths(['/path/to/config', '/path/to/dir'])
confight.load(['/path/to/config.toml', '/path/to/dir/droplet.toml'])
```

Each function offers different parameters to improve the ease of use.

The extension of the configuration file can be given with the `extension`
parameter. For instance, `load_app('myapp', extension='json')` would look for
the `/etc/myapp/config.json` file.

All files in the `conf.d` directory are read by default regardless the
extension. To enforce that only `.extension` files are read, add the
`force_extension` flag.

## Parsing

Given a path to an existing configuration file, it will be loaded in memory
using basic types (`string`, `int`, `float`, `list`, `dict`).

The given file can be in one of the allowed formats. For a complete list see
the `confight.FORMATS` list.

```
confight.parse('/path/to/config', format='toml')
```

When no format is given, it tries to guess by looking at file extensions:

```
confight.parse('/path/to/config.json')  # will gess json format
```

You can see the list of all available extensions at `confight.FORMAT_EXTENSIONS`.

A custom parsing can be provided by passing a `parser` function to the `load`
family of functions, matching the signature:

```python
def parser(path, format=None)
```

The function takes a filesystem `path` and a `format` and  the result should
be a single dictionary with all the loaded data.  When `format` is *None* the
parser is expected to guess it.

## Merging

Given a list of parsed configs in order, merge them into a single one.
For values that appears several times, the last one wins.

Sections and subsections are recursively merged, keeping all keys along the
way and overriding the ones in more than one file with the latest appearance.

A custom merging can be provided by passing a `merger` function to the `load`
family of functions, matching the signature:

```python
def merger(configs)
```

The function takes a list of dictionaries containing the parsed configuration
in ascending order of priority. It should return a single dictionary with all
the configuration.

## Finding configs

The default behaviour is that all files at the `conf.d` directory will be
opened, in lexicographical order, and parsed.

A custom config locator can be provided by passing a `finder` function to the
`load` family of functions, matching the signature:

```python
def finder(path)
```

The function takes a filesystem path (a `conf.d` directory supposedly) and
returns a list of paths to config files in the desired order of parsing and
merging, this is from less to more priority for their values.

## Examples

Load application config from the default locations by using the `load_app`
function which will look by default at the `/etc/myapp/config.toml` and
configuration directory at `/etc/myapp/conf.d`:

```
# /etc/myapp/config.toml    # /etc/myapp/conf.d/production.toml
user = myapp                password = aX80@klj
password = guest
```

```python
>>> confight.load_app('myapp')
{
  "user": "myapp",
  "password": "aX80@klj"
}
```

Allow the user to override the default value when wanting to use a different
configuration. When *None* is given, the default is used:

```python
import argparse
import confight

parser = argparse.ArgumentParser()
parser.add_argument('--config', default=None)
parser.add_argument('--config-dir', default=None)
args = parser.parse_args()

config = confight.load_app('myapp',
                           file_path=args.config,
                           dir_path=args.config_dir)
```

If the application supports user configuration the function `load_user_app`
might come handy as it will first load the regular app config and then the one
defined in the user directory `~/.config/myapp/config.toml` and
`~/.config/myapp/conf.d/*`:

```
# /etc/myapp/config.toml      # ~/.config/myapp/conf.d/mysettings.toml
url = http://teg.avature.net  password = Avature123!
```

```python
>>> confight.load_user_app('myapp')
{
  "url": "http://teg.avature.net",
  "password": "Avature123!"
}
```

To ignore config file extensions, set a *format* and all files will be parsed
using such:

```
# /etc/myapp/config.toml      # /etc/myapp/config.d/extra
name = test                   name = erebus
```

```python
>>> confight.load_app('myapp', format='toml')
{
    "name": "erebus"
}
```

To load configs from a *dev* or *debug* location use the `prefix` option.
This will change the base to calculate default paths.

```python
# Loads from ./configs/config.toml and ./configs/config.d/*
>>> confight.load_app('myapp', prefix='./configs')
```

The `user_prefix` option can be used altogether for user config files:

```python
# Loads from regular places and ./user/config.toml and ./user/config.d/*
>>> confight.load_user_app('myapp', user_prefix='./user')
```

Added in version 1.0

## Command line

*confight* allows to inspect configuration from the command line.

By using the *confight* command it would load the *myapp* configuration from
it's default places and display the output in toml format:

    confight show myapp

This allows to preview the resulting config for an application after all
merges have been resolved. It can come handy when figuring out what the
application has loaded or to debug complex config scenarios.

By passing the `--verbose INFO` interesting data such as all visited files is
listed.

Added in version 0.3

### Command line options

    usage: confight [-h] [--version] [-v {DEBUG,INFO,WARNING,ERROR,CRITICAL}]
                    {show} ...

    One simple way of parsing configs

    positional arguments:
    {show}

    optional arguments:
    -h, --help            show this help message and exit
    --version             show program's version number and exit
    -v {DEBUG,INFO,WARNING,ERROR,CRITICAL}, --verbose {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                            Logging level default: ERROR ['DEBUG', 'INFO',
                            'WARNING', 'ERROR', 'CRITICAL']

## Installation

Install it via pip using:

    pip install confight

Also with *yaml* support:

    pip install confight[yaml]

## Development

Run application tests

    tox

Install the application and run tests in development:

    pip install -e .
    python -m pytest

Changelog
=========

* 1.2.2 (2019-02-19)

  * [7344c929] Fixes man generation in debian rules

* 1.2.1 (2019-02-19)

  * [491f8b05] Fixes find path expansion

* 1.2 (2019-02-14)

  * [3c266c8d] Force all loaded files to have the same extension

* 1.1.1 (2019-01-31)

  [ javier.lasheras ]
  * [a1646871] OrderedDict for yaml too

* 1.1 (2019-01-29)

  * [4a5920af] Adds pypi version badge to README
  * [59c47a5e] Drops support for Python 3.3 and Python 3.4
  * [dfa9c436] Adds support for Python 3.7
  * [6979074d] Fix manpage generation
  * [8f6b58f5] Create a parser with ExtendedInterpolation
  * [7d74246d] Avoid DeprecationWarnings
  * [633b1571] Ordered dicts everywhere

* 1.0 (2018-06-26)

  * [736a6493] Adds prefix and user_prefix options
  * [023158e5] Adds --prefix and --user-prefix cli options
  * [f395fc44] Adapt tests to run in python 3.3 and 3.4
  * [a144dab1] Update package metadata

* 0.3 (2018-06-14)

  * [a7b46ef1] Adds travis config file
  * [5f625da9] Add tox-travis integration
  * [1b678173] Adds confight command line tool
  * [691e042a] Adds cli unit tests

* 0.2.2 (2018-04-13)

  * [3322a7a4] Allow custom file extensions when format is defined

* 0.2.1 (2018-04-09)

  * [93cd8a1c] Update README

* 0.2 (2018-04-04)

  * [63d55fa8] Add Yaml support

* 0.1.1 (2018-04-03)

  * [80087037] Allows to pass extra paths in load functions

* 0.1.0 (2018-03-27)

  * [23927421] Reorganize pretty functions and find behaviour
  * [fade6dd0] Adds debian packaging
  * [c818857a] Update README

* 0.0.1 (2018-03-27)

  * Initial release.

