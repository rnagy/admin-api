# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2021 grammm GmbH

from . import Cli
from argparse import ArgumentParser

def _human(size):
    units = ("B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB")
    index = 0
    while size >= 1024 and index < len(units)-1:
        index += 1
        size /= 1024
    return size, units[index]


def _du(path):
    import os
    files, size = 0, os.path.getsize(path)
    for pathname, dirnames, filenames in os.walk(path):
        for filename in dirnames+filenames:
            file = os.path.join(pathname, filename)
            if not os.path.islink(file):
                files += os.path.isfile(file)
                size += os.path.getsize(file)
    return files, size


def _statStr(files, size):
    human = "" if size < 1024 else " ("+Cli.col("{:.3n} {}".format(*_human(size)), attrs=["bold"])+")"
    return f"{size:,} bytes{human} used by "+Cli.col(f"{files} file"+("" if files == 1 else "s"), attrs=["bold"])


def cliFsDu(args):
    from tools.config import Config
    files = size = 0
    if args.partition is None or args.partition == "domain":
        prefix = Config["options"]["domainPrefix"]
        f, s = _du(prefix)
        files += f
        size += s
        print(prefix+": "+_statStr(f, s))
    if args.partition is None or args.partition == "user":
        prefix = Config["options"]["userPrefix"]
        f, s = _du(prefix)
        files += f
        size += s
        print(prefix+": "+_statStr(f, s))
    if args.partition == None:
        print(_statStr(files, size))


def _clean(path, used, maxdepth, du=False, delete=True):
    import os
    import shutil
    path = path.rstrip(os.path.sep)
    prefix = len(path)
    maxdepth -= 1
    files = size = 0
    for pathname, dirnames, filenames in os.walk(path):
        depth = pathname[prefix:].count(os.path.sep)
        if depth > maxdepth:
            dirnames.clear()
            continue
        if depth < maxdepth:
            continue
        removed = 0
        for dirname in dirnames:
            dp = os.path.join(pathname, dirname)
            if dp not in used:
                removed += 1
                if du:
                    f, s = _du(dp)
                    files += f
                    size += s
                print("Remov{} {}".format("ing" if delete else "e", Cli.col(dp, attrs=["bold"])))
                if delete:
                    shutil.rmtree(dp, ignore_errors=True)
        if len(dirnames)-removed <= 0 and depth != 0:
            size += os.path.getsize(pathname)
            print("Removing empty directory "+Cli.col(pathname, attrs=["bold"]))
            if delete:
                try: os.rmdir(pathname)
                except: pass
        dirnames.clear()
    return files, size


def cliFsClean(args):
    Cli.require("DB")
    from tools.config import Config
    opt = Config["options"]
    files = size = 0
    if args.partition is None or args.partition == "domain":
        from orm.domains import Domains
        used = {d.homedir for d in Domains.query.with_entities(Domains.homedir).filter(Domains.homedir != "").all()}
        f, s = _clean(opt["domainPrefix"], used, opt["domainStorageLevels"], not args.nostat, not args.dryrun)
        files += f
        size += s
    if args.partition is None or args.partition == "user":
        from orm.users import Users
        used = {u.maildir for u in Users.query.with_entities(Users.maildir).filter(Users.maildir != "").all()}
        f, s = _clean(opt["userPrefix"], used, opt["userStorageLevels"], not args.nostat, not args.dryrun)
        files += f
        size += s
    if not args.nostat:
        print(("Operation would free " if args.dryrun else "Freed ")+_statStr(files, size))


def _setupCliFsParser(subp: ArgumentParser):
    sub = subp.add_subparsers()
    clean = sub.add_parser("clean", help="Remove unused user and domain files")
    clean.description = "Delete domain and user directories that may be left behind when removing a domain or user without "\
                        "deleteFiles directive"
    clean.set_defaults(_handle=cliFsClean)
    clean.add_argument("partition", nargs="?", choices=("domain", "user"), help="Clean only specified partition")
    clean.add_argument("-d", "--dryrun", action="store_true", help="Do not actually delete anything")
    clean.add_argument("-s", "--nostat", action="store_true", help="Do not collect disk usage of deleted files")
    du = sub.add_parser("du", help="Show disk usage")
    du.set_defaults(_handle=cliFsDu)
    du.add_argument("partition", nargs="?", choices=("domain", "user"), help="Partition to calculate disk usage for")


@Cli.command("fs", _setupCliFsParser, help="Filesystem operations")
def cliFsStub(args):
    pass
