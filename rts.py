#!/bin/python3
import hawkey
import rpm
from os import listdir, getcwd


class RpmTag(object):
    '''
    Object representation of rpm tag. Used to build reduced transaction
    set header from hawkey sack that can be sorted with the same result
    as sort on fully defined transaction set
    '''

    def __init__(self, hy_rel_dep):
        '''
        Constructs rpm tag
        :param hy_rel_dep: hawkey Reldep class instance
        '''
        items = hy_rel_dep.__str__().split()
        self.name = items[0]
        self.separator = ''
        self.version = ''
        self.release = ''
        self.epoch = ''
        if len(items) == 3:
            self.separator = items[1]
            self._get_vre(items[2])
        self._get_flags()

    def _get_flags(self):
        '''
        Adds flags to rpm tag according to rpm specification
        '''
        self.flags = rpm.RPMSENSE_ANY
        if self.separator:
            if '=' in self.separator:
                self.flags |= rpm.RPMSENSE_EQUAL
            if '>' in self.separator:
                self.flags |= rpm.RPMSENSE_GREATER
            if '<' in self.separator:
                self.flags |= rpm.RPMSENSE_LESS
        if 'rpmlib' == self.name[:6]:
            self.flags |= rpm.RPMSENSE_RPMLIB

    def _get_vre(self, version):
        '''
        Adds version, release and epoch information to rpm tag
        :param version: string in form of 'version.release.epoch'
        '''
        items = version.split('.')
        self.version = items[0]
        if len(items) >= 2:
            self.release = items[1]
        if len(items) == 3:
            self.epoch = items[2]

    def get_name(self):
        '''
        rpm tag name getter
        :return: name in bytes format (appendable to transaction set header)
        '''
        return bytes(self.name, 'utf-8')

    def get_flags(self):
        '''
        rpm tag flags name getter
        :return: flags integer
        '''
        return self.flags

    def get_version(self):
        '''
        rpm tag version getter
        :return: version string in bytes type (appendable to transaction set header)
        '''
        s = self.version
        if self.release:
            s += '.' + self.release
        if self.epoch:
            s += '.' + self.epoch
        return bytes(s, 'utf-8')

    def get_tag(self):
        '''
        rpm tag NVRE getter
        :return: name version release epoch string in bytes format (comparable to transaction set header tag NVRE)
        '''
        s = self.name
        if self.separator:
            s += ' ' + self.separator
        if self.version:
            s += ' ' + self.version
        return bytes(s, 'utf-8')

    def __str__(self):
        '''
        :return: string representation of rpm tag
        '''
        return self.name + ' ' + self.separator + ' ' + self.version

    def __dict__(self):
        '''
        :return: dict representation of rpm tag
        '''
        d = dict()
        d['name'] = self.name
        d['separator'] = self.separator
        d['version'] = self.version
        d['flags'] = self.flags
        return d


def build_reduced_sorted_ts(repo_path, srpm_path):
    '''
    Builds reduced transaction set with sorted list of
    keys (packages)
    :param repo_path: path to directory containing `filelists.xml.gz`, `primary.xml.gz` and `repomd.xml`
    :param srpm_path: path to directory containing list of source RPM added to transaction through cmdline
    :return: transaction set for given input repo and source_rpms (srpms have to be within the repository) or None
    '''
    sack = hawkey.Sack(cachedir=getcwd(), arch='x86_64')
    repo = hawkey.Repo('test')

    for f in listdir(repo_path):
        file = repo_path + f
        if file.endswith('.xml'):
            repo.repomd_fn = file
        elif file.endswith('filelists.xml.gz'):
            repo.filelists_fn = file
        elif file.endswith('primary.xml.gz'):
            repo.primary_fn = file

    sack.load_repo(repo, build_cache=True, load_filelists=True)
    # print(len(sack))

    package = None
    for file in listdir(srpm_path):
        if file.endswith('src.rpm'):
            package = sack.add_cmdline_package(srpm_path + file)
            # print(package)

    if not package:
        return None

    ts = rpm.TransactionSet()
    goal = hawkey.Goal(sack)
    goal.install(package)
    goal.run(ignore_weak_deps=True)

    for pkg in goal.list_installs():
        h = rpm.hdr()
        h[rpm.RPMTAG_NAME] = pkg.name
        h[rpm.RPMTAG_VERSION] = pkg.version
        h[rpm.RPMTAG_RELEASE] = pkg.release
        h[rpm.RPMTAG_EPOCH] = pkg.epoch
        h[rpm.RPMTAG_ARCH] = pkg.arch
        h[rpm.RPMTAG_OS] = 'linux'

        requires = list()
        require_version = list()
        require_flags = list()
        provides = list()
        provide_version = list()
        provide_flags = list()

        for p in pkg.provides:
            t = RpmTag(p)
            provides.append(t.get_name())
            provide_version.append(t.get_version())
            provide_flags.append(t.get_flags())

        for p in pkg.requires:
            t = RpmTag(p)
            requires.append(t.get_name())
            require_version.append(t.get_version())
            require_flags.append(t.get_flags())

        for p in pkg.requires_pre:
            t = RpmTag(p)
            requires.append(t.get_name())
            require_version.append(t.get_version())
            require_flags.append(t.get_flags() | rpm.RPMSENSE_PREREQ)

        if provides:
            h[rpm.RPMTAG_PROVIDES] = provides
        if provide_flags:
            h[rpm.RPMTAG_PROVIDEFLAGS] = provide_flags
        if provide_version:
            h[rpm.RPMTAG_PROVIDEVERSION] = provide_version
        if requires:
            h[rpm.RPMTAG_REQUIRES] = requires
        if require_flags:
            h[rpm.RPMTAG_REQUIREFLAGS] = require_flags
        if require_version:
            h[rpm.RPMTAG_REQUIREVERSION] = require_version

        ts.addInstall(h, pkg.name, 'i')

    ts.order()
    return ts

# example usage printing all keys in order (test this order)

'''
if __name__ == "__main__":
    REPO_PATH = getcwd() + '/repodata/'
    RPM_PATH = getcwd() + '/srpm/'
    t = build_reduced_sorted_ts(REPO_PATH, RPM_PATH)
    # t is already sorted here

    for pkg in t.getKeys():
        print(pkg)

    with open('rts_input.txt', 'w') as f:
        for pkg in t.getKeys():
            f.write(pkg + '\n')
'''
