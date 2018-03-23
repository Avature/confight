% confight(1)
% Platform Team
% March 2018

confight
========

Parse configurations like a pr0.

- Extensible config via `conf.d` directory
- Allow for multiple formats (*toml*, *json*, *ini*)
- Full unicode support
- Personalize every aspect when needed
- Autodetect file formats

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

## Rationale

We all agree that changing config files using nothing but *sed* or your bare
hands is nasty, isn't it?

The *right* way of extending and changing configuration, either by hand or
from scripts, is to create a new small config file and place it at the
application `conf.d` directory, from where it will be parsed and merged nicely
into a single final configuration.

This allows to separate configs in different topics, make modifications and
extensions all without messing with already existing defaults or deleting or
moving protected files.

This is specially good for *debian-packaged* applications, beacause modified
files won't get updated with new configs for the next version, and so they'll
stay forever unless manually merged (Yes, I've said 💩MANUALLY!💩💩).  By
placing new files in those directories, application configuration can change
be extended and overriden without getting dirty.

The idea is to "*map reduce*" configurations, by parsing all files in
order and then merge them into a single config that holds all the data:

```
 C₀ -- parse -----|
    C₁ -- parse --|
    C₂ -- parse --|-- merge --> C
       ⋮          |
    Cₙ -- parse --|
```

## Droplets

A **droplet** is a small config file that is *dropped* into a `conf.d`
directory so the application can parse and merge it with the rest of the
config.

This allows to extend and override config values by creating new files instead
of messing with existing configurations which is always tricky.

This approach is very common in Linux and used in cron (`/etc/cron.d`), bash
profiles (`/etc/profile.d`), apt (`/etc/apt/sources.list.d`), systemd and many
other.s

The name of those files will determine the order in which they're parsed and
the priority their values will have when merging.

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

Load application config from default location by using the `load_app` function
which will look by default at the `/etc/myapp/config.toml` and configuration
directory at `/etc/myapp/conf.d`:

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

## Development

Run the application tests

    tox

Install the application and run tests in development:

    pip install -e .
    python -m pytest

Changelog
=========
