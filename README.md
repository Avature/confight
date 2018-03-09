% confight(1)
% Platform Team
% March 2018

confight
========

Parse configurations like a pr0.

- Extensible config via `conf.d` directory.
- Allow for multiple formats (*toml*, *json*, *ini*)
- Autodetect file formats
- Full unicode support
- Personalize every aspect when needed

```python
import confight

config = confight.load_app('myapp')
print(config)
{
    "section": {
        "key": "value"
    }
}
```

The previous fragment got all the config files at `/etc/myapp/config.toml` and
within the `/etc/myapp/conf.d` directory and merged them into a single config.

```toml
# /etc/myapp/config.toml    /etc/myapp/conf.d/00_first.json    /etc/myapp/conf.d/99_second.ini
[section]                   {                                  [section]
key = "base config"           "section": {                     key = value
                                 "key": "not this"
                              }
                            }
```

## Droplets

We all agree that changing config files using nothing but *sed* or your bare
hands is nasty, RIGHT?

The *right* way of extending and changing configuration, either by hand or
from scripts, is to create a new small config file and place it at the
`conf.d` directory, from where it will be parsed and merged nicely into a
single final configuration.

This allows to separate config topics, modifications and extensions, without
messing with already existing default files or deleting or moving files.

This is specially good for *debian-packaged* applications, beacause modified
files won't get updated with new configs for the next version, and so they'll
stay forever unless manually merged (Yes, I've said MANUALLY! 💩💩💩).
By placing new files in those directories, application configuration can
change be extended and overriden without getting dirty.

## Parsing

All files are parsed using the given format to the `load` family of functions:

```python
confight.load(['config'], format='toml')
```

For a complete list of allowed formats see the `confight.FORMATS` list.

When no format is given, it tries to guess by looking at file extensions:

```
confight.load(['config.json'])  # will gess json format
```

You can see the list of available extensions at `confight.FORMAT_EXTENSIONS`.

A custom parsing can be provided by passing a `parser` function to the `load`
family of functions, matching the signature:

```python
def parser(path, format=None)
```

The function takes a filesystem `path` and a `format` and  the result should be a
single dictionary with all the loaded data.  When `format` is *None* the parser
is expected to guess it.


## Merging

Given a list of configuration files in order, the values in the last file
wins. 

Sections, subsections and maps are recursively merged, keeping all keys along
the way and overriding the ones in more than one file with the latest
appearance.

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

## Development

Run the application tests

    tox

Install the application and run tests in development:

    pip install -e .
    python -m pytest
