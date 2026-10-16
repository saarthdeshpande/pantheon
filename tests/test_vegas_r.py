#!/usr/bin/env python

'''Builds and runs the VegasR unit tests (below / equal / above the
threshold, cwnd floor, required R, skipped rounds, once-per-RTT updating).
Requires the patched third_party/ccmatic_genericCC (see src/wrappers/vegas_r.py
setup) and g++.'''

import os
import subprocess
import tempfile
import unittest
from os import path

import context


class TestVegasR(unittest.TestCase):
    def test_cpp_unit_tests(self):
        repo = path.join(context.base_dir, 'third_party', 'ccmatic_genericCC')
        if not path.exists(path.join(repo, 'vegas_r_test.cc')):
            self.skipTest('run "src/wrappers/vegas_r.py setup" first')

        exe = path.join(tempfile.mkdtemp(), 'vegas_r_test')
        subprocess.check_call(
            ['g++', '-std=c++11', '-Wall', '-Wextra', '-Werror', '-I.',
             'vegas_r_test.cc', 'vegas_r.cc', '-o', exe], cwd=repo)
        out = subprocess.check_output([exe])
        self.assertIn('ALL PASSED', out.decode())

    def test_r_is_required(self):
        wrapper = path.join(context.src_dir, 'wrappers', 'vegas_r.py')
        env = dict(os.environ, VEGAS_R='0')
        p = subprocess.Popen(['python2', wrapper, 'sender', '127.0.0.1', '1'],
                             env=env, stderr=subprocess.PIPE)
        _, err = p.communicate()
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('positive', err.decode())


if __name__ == '__main__':
    unittest.main()
