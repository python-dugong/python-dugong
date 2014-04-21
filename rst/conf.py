# -*- coding: utf-8 -*-
#pylint: disable-all
#@PydevCodeAnalysisIgnore

import sys
import os.path

sys.path.append(os.path.abspath('..'))

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx' ]
intersphinx_mapping = {'python': ('http://docs.python.org/3/', None) }
templates_path = ['_templates']
source_suffix = '.rst'
source_encoding = 'utf-8'
master_doc = 'index'
nitpicky = True
project = u'Dugong'
copyright = u'2013-2014, Nikolaus Rath'
default_role = 'py:obj'
primary_domain = 'py'
add_module_names = False
autodoc_member_order = 'groupwise'
pygments_style = 'sphinx'
highlight_language = 'python'
html_theme = 'default'
html_use_modindex = False
html_use_index = True
html_split_index = False
html_show_sourcelink = False

