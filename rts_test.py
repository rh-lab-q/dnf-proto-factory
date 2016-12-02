#!/bin/python3

import os
import rpm
import rts
import subprocess


class RPMHeaderTest():

    def __init__(self, t):
        self.tested = t
        self.path = "tmp/"

    def downloadPackage(self, package):
        print("Starting downloading package:\n" + package)
        if ".src" in package:
            cmd = "dnf download --destdir tmp --source "
        else:
            cmd = "dnf download --destdir tmp "
        try:
            subprocess.check_output(["bash", "-c", cmd + package])
        # For case dnf can't find package
        except subprocess.CalledProcessError:
            pass

    def getHeader(self, package):
        fd = os.open(package, os.O_RDONLY)
        header = self.ts.hdrFromFdno(fd)
        os.close(fd)
        return header

    def setUp(self):
        self.ts = rpm.TransactionSet()
        # Set flags to NOT controle public key
        # (otherwise there can be an error: public key not available)
        self.ts.setVSFlags(rpm._RPMVSF_NOSIGNATURES)

        for pkg in self.tested:
            h = rpm.hdr()
            h[rpm.RPMTAG_NAME] = pkg.N()
            h[rpm.RPMTAG_VERSION] = pkg.V()
            h[rpm.RPMTAG_RELEASE] = pkg.R()
            h[rpm.RPMTAG_ARCH] = pkg.A()
            h[rpm.RPMTAG_OS] = 'linux'
            package = h.NEVRA.decode('utf-8')
            self.downloadPackage(package)

        for f in os.listdir(self.path):
            file = self.path + f
            h = self.getHeader(file)
            self.ts.addInstall(h, h.name.decode('utf-8'), 'i')

        self.ts.order()
        with open('rts_output.txt', 'w') as f:
            for pkg in self.ts.getKeys():
                f.write(pkg + '\n')

        try:
            ret = subprocess.check_output(['bash', '-c', 'diff rts_input.txt rts_output.txt > diffed'])
            if len(ret) == 0:
                print('Test passed')
        except subprocess.CalledProcessError:
            print('Test failed. For more information read diffed file')


if __name__ == "__main__":
    REPO_PATH = os.getcwd() + '/repodata/'
    RPM_PATH = os.getcwd() + '/srpm/'
    t = rts.build_reduced_sorted_ts(REPO_PATH, RPM_PATH)

    with open('rts_input.txt', 'w') as f:
        for pkg in t.getKeys():
            f.write(pkg + '\n')

    RPMTest = RPMHeaderTest(t)
    RPMTest.setUp()
