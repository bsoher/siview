# Python modules


# 3rd party modules
import setuptools


VERSION = open("VERSION").read().strip()

NAME = "SIView"

DESCRIPTION = """Washout is a command line and GUI based application for processing dynamic lung imaging data."""

LONG_DESCRIPTION = """
Washout is a software package written in Python that allows the user to 
visualize dynamic lung images and fit ventilation time course data to a
parametric model. Results can be saved to CSV or DICOM formats. The software
has both GUI and command line modes.
"""
MAINTAINER = "Dr. Brian J. Soher"
MAINTAINER_EMAIL = "bsoher ~at~ briansoher ~dot com~"
# http://pypi.python.org/pypi?:action=list_classifiers
CLASSIFIERS = [ "Development Status :: 4 - Beta",
                "Intended Audience :: Science/Research",
                "Intended Audience :: Healthcare Industry",
                "License :: OSI Approved :: BSD License",
                "Operating System :: Microsoft :: Windows",
                "Programming Language :: Python :: 3.9",
              ]
LICENSE = "http://creativecommons.org/licenses/BSD/"
PLATFORMS = 'Windows'
KEYWORDS = "mrs, spectroscopy, time analysis, frequency domain, parametric"

setuptools.setup(name=NAME,
                 version=VERSION,
                 packages=setuptools.find_packages(),
                 entry_points = {
                         "console_scripts": ['siview = siview.siview:main']
                 },
                 maintainer=MAINTAINER,
                 maintainer_email=MAINTAINER_EMAIL,
                 zip_safe=False,
                 include_package_data=True,
#                 classifiers=CLASSIFIERS,
#                 license=LICENSE,
                 description=DESCRIPTION,
                 long_description=LONG_DESCRIPTION,
                 platforms=PLATFORMS,
                 keywords=KEYWORDS,
                 # setuptools should be installed along with SIView; the latter requires the
                 # former to run. (SIView uses setuptools' pkg_resources in get_siview_version()
                 # to get the package version.) Since SIView is distributed as a wheel which can
                 # only be installed by pip, and pip installs setuptools, this 'install_requires'
                 # is probably superfluous and just serves as documentation.
                 install_requires=['setuptools'],
                 )
