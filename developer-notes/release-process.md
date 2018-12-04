#. Update version in ``dugong/__init__.py``
#. Add release date to ``Changes.rst``
#. Check ``hg status -u``, if necessary run ``hg purge`` to avoid undesired files in the tarball.
#. ``hg commit -m "Released xy"``
#. ``hg tag release-xy``
#. ``./setup.py build_sphinx``
#. ``./setup.py sdist``
#. Extract tarball in temporary directory and test:
  #. ``./setup.py build_sphinx``
  #. ``python3 -m pytest test/``
#. ``./setup.py upload_docs``
#. ``./setup.py sdist upload --sign``
#. Push changes
