# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2020 grammm GmbH

from . import Cli, ArgumentParser


def _runParserSetup(subp: ArgumentParser):
    subp.add_argument("--ip", "-i", default="0.0.0.0", type=str, help="Host address to bind to")
    subp.add_argument("--port", "-p", default=5001, type=int, help="Host port to bind to")
    subp.add_argument("--debug", "-d", action="store_true", help="Run in debug mode")
    subp.add_argument("--no-config-check", action="store_true", help="Skip configuration check")


@Cli.command("run", _runParserSetup)
def cliRun(args):
    if not args.no_config_check:
        from tools import config
        error = config.validate()
        if error:
            print("Invalid configuration found: "+error)
            return 1
    from api.core import API
    import endpoints
    import importlib
    for group in endpoints.__all__:
        importlib.import_module("endpoints."+group)
    API.run(host=args.ip, port=args.port, debug=args.debug)


def _versionParserSetup(subp: ArgumentParser):
    subp.add_argument("--api", "-a", action="store_true", help="Print API version")
    subp.add_argument("--backend", "-b", action="store_true", help="Print Backend version")
    subp.add_argument("--combined", "-c", action="store_true", help="Print combined version")


@Cli.command("version", _versionParserSetup)
def cliVersion(args):
    from api import backendVersion, apiVersion
    if args.api:
        print(apiVersion)
    if args.backend:
        print(backendVersion)
    if args.combined or not any((args.api, args.backend, args.combined)):
        vdiff = int(backendVersion.rsplit(".", 1)[1])-int(apiVersion.rsplit(".", 1)[1])
        if vdiff == 0:
            print(apiVersion)
        else:
            print("{}{:+}".format(apiVersion, vdiff))


@Cli.command("chkconfig")
def cliChkConfig(args):
    from tools.config import validate
    result = validate()
    if result is None:
        print("Configuration schema valid")
        return 0
    else:
        print("Error: "+result)
        return 1

def _cliTaginfoCompleter(prefix, **kwargs):
    from tools.constants import PropTags
    PropTags.lookup(None)
    c = []
    if prefix == "" or prefix[0].islower():
        c += [tag.lower() for value, tag in PropTags._lookup.items() if isinstance(value, int)]
    if prefix == "" or prefix[0].isupper():
        c += [tag.upper() for value, tag in PropTags._lookup.items() if isinstance(value, int)]
    if prefix == "" or prefix[0] == "0" and (len(prefix) <= 2 or not prefix[2:].isupper()):
        c += ["0x{:08x}".format(value) for value in PropTags._lookup.keys() if isinstance(value, int)]
    if prefix == "" or prefix[0] == "0" and (len(prefix) <= 2 or not prefix[2:].islower()):
        c += ["0x{:08X}".format(value) for value in PropTags._lookup.keys() if isinstance(value, int)]
    if prefix == "" or prefix.isnumeric():
        c += [str(value) for value in PropTags._lookup.keys() if isinstance(value, int)]
    return c


def _setupTaginfo(subp: ArgumentParser):
    tagID = subp.add_argument("tagID", nargs="+", help="Numeric tag ID in decimal or hexadecimal or tag name")
    tagID.completer = _cliTaginfoCompleter


@Cli.command("taginfo", _setupTaginfo)
def cliTaginfo(args):
    from tools.constants import PropTags, PropTypes
    for tagid in args.tagID:
        try:
            ID = int(tagid, 0)
        except:
            ID = getattr(PropTags, tagid.upper(), None)
            if ID is None or type(ID) != int:
                print("Unknown tag '{}'".format(tagid))
                continue
        propname = PropTags.lookup(ID, "unknown")
        proptype = PropTypes.lookup(ID, "unknown")
        print("0x{:x} ({}): {}, type {}".format(ID, ID, propname, proptype))


def _setupCliBatchMode(subp: ArgumentParser):
    subp.description = "Start batch mode to process multiple CLI calls in a single session"


@Cli.command("batch")
def cliBatchMode(args):
    import shlex
    import sys
    interactive = sys.stdin.isatty()
    if interactive:
        print("grammm-admin batch mode. Type exit or press CTRL+D to exit.")
    try:
        while True:
            command = input("grammm-admin> " if interactive else "").strip()
            if command == "":
                continue
            elif command == "exit":
                break
            try:
                Cli.execute(shlex.split(command))
            except SystemExit:
                pass
    except KeyboardInterrupt:
        print("Received interrupt - exiting")
    except EOFError:
        print()
