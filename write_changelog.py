"""Write README changelog section from debian Changelog section"""
from __future__ import print_function

import io
import re
import datetime
import email.utils


def write_changelog():
    with io.open('README.md', 'r+', encoding='utf8') as stream:
        remove_old_changelog(stream)
        stream.writelines(get_changes())


def get_changes():
    with io.open('debian/changelog', encoding='utf8') as stream:
        yield u"\n"
        for change in parse_changelog(stream):
            yield u"* {version} ({date})\n{changes}".format(**change)


def parse_changelog(stream):
    context = {}
    for line in stream:
        header = _detect_header(line)
        footer = _detect_footer(line)
        if header:
            context = header
        elif footer:
            context.update(footer)
            yield context
        else:
            context['changes'] = context.get('changes', '') + line


_changelog_re = re.compile('^Changelog *$')


def remove_old_changelog(stream):
    for line in iter(stream.readline, ''):
        if _changelog_re.match(line):
            # truncate at next line
            stream.readline()
            stream.truncate(stream.tell())
            stream.seek(0, 1)
            return

    raise Exception(u'Could not find Changelog section')


_header_re = re.compile('^(?P<name>\w+) \((?P<version>.+)\) \w+; \w+=\w+')


def _detect_header(line):
    match = _header_re.match(line)
    if match:
        return match.groupdict()


_footer_re = re.compile('^ -- [^<]+ \<[^>]+\> (?P<date>.*)')


def _detect_footer(line):
    match = _footer_re.match(line)
    if match:
        return dict(date=parse_changelog_date(match.group('date')))


def parse_changelog_date(text):
    return datetime.datetime(*email.utils.parsedate(text)[:6]).strftime('%Y-%m-%d')


if __name__ == '__main__':
    write_changelog()
