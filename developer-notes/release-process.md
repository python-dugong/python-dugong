#. Update version in ``dugong/__init__.py``
#. Add release date to ``Changes.rst``
#. Check for untracked files (and make sure they don't end up in the tarball)
#. ``git commit -m "Released xy"``
#. ``git tag -s release-xy``
#. ``./setup.py build_sphinx``
#. ``./setup.py sdist``
#. Extract tarball in temporary directory and test:
  #. ``./setup.py build_sphinx``
  #. ``python3 -m pytest test/``
#. ``./setup.py upload_docs``
#. ``./setup.py sdist upload --sign``
#. `git push && git push --tags`
