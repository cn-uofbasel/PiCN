import sys, os

# append the next line to conf.py, should change "backend" to your module name
sys.path.insert(0, os.path.join(os.path.dirname(__file__),'..','PiCN'))

# ensure the autodoc and napoleon are in the extensions
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.napoleon']

def run_apidoc(_):
    from sphinx.apidoc import main
    parentFolder = os.path.join(os.path.dirname(__file__), '..')
    cur_dir = os.path.abspath(os.path.dirname(__file__))
    sys.path.append(parentFolder)
    # change "backend" to your module name
    module = os.path.join(parentFolder,'PiCN')
    output_path = os.path.join(cur_dir, 'api')
    main(['-e','-f','-o', output_path, module])

def setup(app):
    # overrides for wide tables in RTD theme
    app.add_stylesheet('theme_overrides.css')
    # trigger the run_apidoc
    app.connect('builder-inited', run_apidoc)
