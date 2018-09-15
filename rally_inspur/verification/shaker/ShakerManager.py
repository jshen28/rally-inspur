from rally.verification import manager
from rally.cli import cliutils


# deprecated: start method does not accept pass in parameters
@manager.configure(name="shaker", platform="openstack",
                   default_repo="https://github.com/openstack/shaker.git",
                   context={})
class ShakerManager(manager.VerifierManager):
    """shaker test manager"""

    def __init__(self, *args, **kwargs):
        """
        manager.configure will clone default_repo and install a virtual
        environment along verifier creation
        :param args:
        :param kwargs:
        """
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
        """
        .. code-block:: none

            <object>.totals = {
              "tests_count": <total tests count>,
              "tests_duration": <total tests duration>,
              "failures": <total count of failed tests>,
              "skipped": <total count of skipped tests>,
              "success": <total count of successful tests>,
              "unexpected_success":
                  <total count of unexpected successful tests>,
              "expected_failures": <total count of expected failed tests>
            }

            <object>.tests = {
              <test_id>: {
                  "status": <test status>,
                  "name": <test name>,
                  "duration": <test duration>,
                  "reason": <reason>,  # optional
                  "traceback": <traceback>  # optional
              },
              ...
            }
        :param context:
        :return:
        """

        run_args = context.get("run_args", {})
        zones = run_args.get('zones', [])

        print("I am running", zones)
        return ManagerResult({
            "tests_count": 1,
            "tests_duration": 1.5,
            "failures": 0,
            "skipped": 0,
            "success": 1,
            "unexpected_success": 0,
            "expected_failures": 0
        }, {
            "1": {
                "status": "success",
                "name": "test",
                "duration": 1.5
            }
        })

    def install_extension(self, source, version=None, extra_settings=None):
        pass


class ManagerResult(object):
    """result object"""

    def __init__(self, totals, tests):
        self.totals = totals
        self.tests = tests

