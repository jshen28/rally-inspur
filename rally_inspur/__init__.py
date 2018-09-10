import pbr.version
from rally.common import version as __rally_version__
from rally_inspur.scenarios import test

__rally_version__ = __rally_version__.version_info.semantic_version()
__rally_version__ = __rally_version__.version_tuple()

if __rally_version__ < (0, 12):
    # NOTE(andreykurilin): Rally < 0.12 doesn't care about loading options from
    #   external packages, so we need to handle it manually.

    from rally.common import opts as global_opts

    from rally_openstack.cfg import opts

    # ensure that rally options are registered.
    global_opts.register()
    global_opts.register_opts(opts.list_opts().items())

__version_info__ = pbr.version.VersionInfo("rally-openstack")
__version__ = __version_info__.version_string()
__version_tuple__ = __version_info__.semantic_version().version_tuple()
