#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
#  - Author:    desko27
#  - Email:     desko27@gmail.com
#  - Version:   1.0.1
#  - Created:   2015/01/28
#  - Updated:   2015/01/31
# ----------------------------------------------------------------------------

from iniparse import INIConfig
from iniparse.config import Undefined
from codecs import open as uopen

# ---------------------------------------------------------------------------
# functions
# ---------------------------------------------------------------------------
conf_exist = lambda e: type(e) != Undefined

# ---------------------------------------------------------------------------
# classes
# ---------------------------------------------------------------------------
class Config:
	""" Shortcuts to the ini parser. Loads `self.x` as the INIConfig object. """
	
	def __init__(self, file): self.x = INIConfig(uopen(file, 'r', 'utf8'))
	def get_sections(self): return [e for e in self.x]
	def get_values_from_section(self, section): return [self.x[section][e] for e in self.x[section]]
