from setuptools import setup, find_packages

setup(name='hubcheck-hubzero-tests',
      version='1.0.0',
      description='hubcheck testsuites hubs hosted by hubzero',
      author='Derrick Kearney',
      author_email='telldsk at gmail dot com',
      packages = find_packages(),
#      install_requires=['hubzero>=1.0.0',
#                       ],
      include_package_data=True,
     )
