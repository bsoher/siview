# Python modules

import os
import logging
import sys
import errno
import os.path
import shutil
import time
import configobj

# 3rd party modules
import wx

# Our modules
#import siview.common.configobj as configobj
import siview.common.util.config as util_config
import siview.common.util.logging_ as util_logging
#import siview.common.util.db_upgrader as db_upgrader
import siview.common.util.misc as util_misc
import siview.common.util.dir_list as dir_list
import siview.common.wx_gravy.common_dialogs as common_dialogs
import siview.common.wx_gravy.util as wx_util
import siview.common.default_ini_file_content as default_ini_file_content
import siview.common.exception_handler as exception_handler

# _ONE_YEAR measures a year in seconds. It's a little sloppy because it doesn't
# account for leap years and that kind of thing, but it's accurate enough for
# how we use it.
_ONE_YEAR = 365 * 24 * 60 * 60


def init_app(app_name):
    """
    The function that all Vespa apps must call to create their wx.App
    object (which this function returns). The caller must pass the app name.
    The app name will be used in messages displayed to the user by this code,
    so it should be something user-friendly like RFPulse, Simulation or
    Analysis.

    There's nothing magic about this code, but it does some important
    housekeeping that we don't want to duplicate in each app.

    Specifically, it does the following --
    - Creates the wx.App object
    - Ensures only one copy of this application is running. It displays a
      message and quits if the app is already running.
    - Sets the wx app name
    - Creates the .vespa object that hangs off of the wx.App object
    - Ensures that Vespa data dir exists. If not it creates it and a new
      database as well.
    - Ensures that Vespa log dir exists, creates it if not.
    - (Re)creates any of our INI files that might be missing.
    - Optionally sets a custom exception hook.
    - If the database is missing, gives the user the option of recreating it
      or exiting the app.

    """
    first_run = False

    # When running under Windows w/pythonw.exe, we have to expicitly send
    # stdout and stderr to the bit bucket.
    # Code below adapted from http://bugs.python.org/issue706263#msg97442
    if (util_misc.get_platform() == "windows") and \
       ("pythonw" in sys.executable.lower()):
       blackhole = open(os.devnull, 'w')
       sys.stdout = sys.stderr = blackhole

    app = wx.App(False)

    app.SetAppName(app_name)

    # Create the Vespa data directory if necessary
    data_dir = util_misc.get_data_dir()
    if not os.path.exists(data_dir):
        # This looks like the first time a Vespa app has been run on this
        # computer.
        first_run = True
        os.mkdir(data_dir)

    # Ensure there isn't another instance of this app running. This code
    # must come after the creation of the app object because if the except
    # clause is triggered it will attempt to show a message box, and it's
    # not valid to do that before the app object exists.
    # Also, it must come after the creation of the data dir because it
    # writes a lock file there.
    try:
        single_instance_enforcer = __SingleAppInstanceEnforcer(app_name)
    except _AlreadyRunningException:
        common_dialogs.message("%s is already running." % app_name)
        sys.exit(-1)

    # Create a directory for log files if necessary
    log_dir = os.path.join(data_dir, "logs")
    if not os.path.exists(log_dir):
        os.mkdir(log_dir)

    _clean_log_files(log_dir)

    # Create any missing INI files.
    for ini_name in ("siview", "analysis", ):
        filename = os.path.join(data_dir, "%s.ini" % ini_name)
        if not os.path.exists(filename):
            _create_ini_file(filename, ini_name)


    # We add to the app object an object of our own. The object doesn't do
    # anything other than create a place for us to attach app-level (global)
    # things. We could attach them directly to the app object but then we
    # run the risk of trashing some wx-specific attribute that has the same
    # name.
    class Anonymous(object):
        """A generic object to which one can attach arbitrary attrs"""
        pass

    app.siview = Anonymous()

    # The singleton enforcer needs to survive for the life of the app so
    # we stash a reference to it in the app object.
    app.siview.single_instance_enforcer = single_instance_enforcer

    # The database name is in siview.ini
    config = util_config.SIViewConfig()

    # Here we deal with the [debug] section of siview.ini.
    
    # We set our custom exception hook as early as possible. Note that it
    # depends on the directory for log files and the existence of siview.ini,
    # so we can't set the exception hook before those exist.
    # The exception hook is on by default but can be turned off by a flag in
    # siview.ini.
    hook_exceptions = True
    if ("debug" in config) and ("hook_exceptions" in config["debug"]):
        hook_exceptions = config["debug"].as_bool("hook_exceptions")

    if hook_exceptions:
        sys.excepthook = exception_handler.exception_hook

    # numpy's response to IEEE 754 floating point errors is configurable.
    # On many platforms these errors are sent to the bit bucket. As
    # developers, we want a chance to hear them loud & clear.
    # See here for details:
    # http://docs.scipy.org/doc/numpy/reference/generated/numpy.seterr.html
    if ("debug" in config) and ("numpy_error_response" in config["debug"]):
        numpy_error_response = config["debug"]["numpy_error_response"]
        if numpy_error_response:
            import numpy
            numpy.seterr(all=numpy_error_response)

    return app


class _AlreadyRunningException(Exception):
    """Indicates that this app is already running. Raised only by the
    __SingleAppInstanceEnforcer class.
    """
    def __init__(self):
        Exception(self)


class __SingleAppInstanceEnforcer(object):
    """A class that ensures only a single instance of the app named in
    app_name (a string passed to the contructor) can be created.

    I swiped most of the code from the URL below and modified it a little
    for Vespa.
    http://stackoverflow.com/questions/380870/python-single-instance-of-program
    """
    def __init__(self, app_name):
        already_running = False

        self.lockfile = "%s.lock" % app_name

        self.lockfile = os.path.join(util_misc.get_data_dir(), self.lockfile)

        if sys.platform.startswith("win"):
            # Windows
            try:
                # The file already exists. This may be because the previous
                # execution was interrupted, so we try to remove the file.
                if os.path.exists(self.lockfile):
                    os.unlink(self.lockfile)
                self.fd = os.open(self.lockfile, os.O_CREAT|os.O_EXCL|os.O_RDWR)
            except OSError as e:
                if e.errno == errno.EACCES:
                    already_running = True
                else:
                    print(e.errno)
                    raise
        else:
            # non Windows. Note that fcntl isn't available on Windows
            import fcntl

            self.fp = open(self.lockfile, 'w')
            try:
                fcntl.lockf(self.fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except IOError:
                already_running = True

        if already_running:
            raise _AlreadyRunningException


    def __del__(self):
        import sys
        if sys.platform.startswith("win"):
            if hasattr(self, 'fd'):
                os.close(self.fd)
                os.unlink(self.lockfile)



def _clean_log_files(log_file_path):
    # This removes any log files that are > 1 year old. This ensures that our
    # log files don't grow infinitely.
    # It assumes the log file path exists, so don't call it until after that
    # path has been created.
    lister = dir_list.DirList(log_file_path, dir_list.FilterFile(),
                                             dir_list.FilterEndsWith(".txt"))

    # This temporary function returns True if a file is more than a year old,
    # False otherwise.
    now = time.time()
    f = lambda filename: (now - int(os.path.getctime(filename))) > _ONE_YEAR

    # Find all files that match
    filenames = [filename for filename in lister.fq_files if f(filename)]

    # Whack 'em.
    list(map(os.remove, filenames))


def _create_ini_file(filename, ini_name):
    # Creates the INI file for an app (rfpulse, sim, or analysis) using
    # default content.
    content = default_ini_file_content.DEFAULT_INI_FILE_CONTENT[ini_name]

    open(filename, "w").write(content)


