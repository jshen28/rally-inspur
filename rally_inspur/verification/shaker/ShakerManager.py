from rally.verification import manager


@manager.configure(name="shaker", platform="openstack",
                   default_repo="https://github.com/openstack/shaker.git",
                   context={})
class ShakerManager(manager.VerifierManager):
    """shaker test manager"""

    def __init__(self, *args, **kwargs):
        super(ShakerManager, self).__init__(*args, **kwargs)

    def override_configuration(self, new_configuration):
        pass

    def uninstall_extension(self, name):
        pass

    def list_tests(self, pattern=""):
        pass

    def configure(self, extra_options=None):
        pass

    def extend_configuration(self, extra_options):
        pass

    def run(self, context):
        print("I am running")

    def install_extension(self, source, version=None, extra_settings=None):
        pass


