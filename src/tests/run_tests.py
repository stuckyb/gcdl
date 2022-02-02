#!/usr/bin/python

# A simple test runner that provides a minimal interface for running tests,
# including automatic test discovery, that produces verbose output by default.
#
# What this script does (without additional arguments) is the same as calling
#
# $ python -m unittest -v
#
# except that this script also implements a path manipulation to ensure that
# the main program packages/modules we wish to test are importable.
#
# You can also test specific test modules using this script, e.g.
#
# $ python run_tests.py TestModule
#


import unittest
import sys
import os.path


# Make sure we can find the source modules.
source_dir = os.path.normpath(
    os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        '../'
    )
)
sys.path.append(source_dir)

if sys.version_info[0] == 3:
    unittest.main(module=None, argv=(sys.argv + ['-v']))
else:
    raise Exception('Python 3 is required.')

