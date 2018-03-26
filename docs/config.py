# markup parser
from recommonmark.parser import CommonMarkParser
source_parsers = {
    '.md': CommonMarkParser,
}
source_suffix = ['.md', '.rst']

# apidoc
from sphinx.apidoc import main
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
cur_dir = os.path.abspath(os.path.dirname(__file__))
module = os.path.join(cur_dir,"..","PiCN")
main(['-e', '-o', cur_dir, module, '--force'])
