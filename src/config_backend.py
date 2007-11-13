#    FlyBack
#    Copyright (C) 2007 Steve Leach
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import gconf
import pickle

"""
Encapsulation of a GConf configuration for Flyback.

Alternative configuration stores (such as Python cfg files
can implement the same interface if required. 
"""
class GConfConfig:

    def get_string(self, key, default=None):
        x = self.client.get_string(key)
        if x:
            return x
        else:
            return default

    def set_string(self, key, value):
        self.client.set_string(key,value)
        
    def get_list(self, key, default=[]):
        x = self.client.get_string(key)
        if x:
            return pickle.loads(x)
        else:
            return default
    
    def set_list(self, key, values):
        self.client.set_string( key, pickle.dumps(values) ) 
    
    def get_bool(self, key):
        return self.client.get_bool(key)
    
    def set_bool(self, key, value):
        self.client.set_bool(key,value)

    def get_int(self, key, default=0):
        x = self.client.get_int(key)
        if x!=None:
            return x
        else:
            return default
    
    def set_int(self, key, value):
        self.client.set_int(key, value)

    """
    Flushes configuration to disk.
    For the FConfConfig this does nothing, but other config
    implementations may need to do something here.
    """
    def flush(self):
        pass

    def __init__(self):
        self.client = gconf.client_get_default()
        self.client.add_dir ("/apps/flyback", gconf.CLIENT_PRELOAD_NONE)
        
        
import unittest

KEY = "/apps/flyback/test/x"

class TestCase(unittest.TestCase):
    
    def setUp(self):
        unittest.TestCase.setUp(self)
        self.cfg = GConfConfig()
    
    def tearDown(self):
        unittest.TestCase.tearDown(self)
        self.cfg.set_string(KEY, "")
        
    def testSetGetString(self):
        self.cfg.set_string(KEY,"abc")
        assert self.cfg.get_string(KEY) == "abc"

    def testSetGetStringList(self):
        vals = ["abc","xyz"]
        self.cfg.set_string_list(KEY, vals)
        assert len(self.cfg.get_string_list(KEY)) == 2
        assert self.cfg.get_string_list(KEY)[0] == "abc"
        assert self.cfg.get_string_list(KEY)[1] == "xyz"
        
    def testSetGetFlag(self):
        self.cfg.set_flag(KEY, True)
        assert self.cfg.get_flag(KEY) == True

    def testSetGetInt(self):
        self.cfg.set_int(KEY, 12321)
        assert self.cfg.get_int(KEY) == 12321
        
if __name__ == '__main__':
    unittest.main()
