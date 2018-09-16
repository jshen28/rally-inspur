from rally_openstack import scenario
from rally_openstack.scenarios.nova import utils
import rally_inspur
import os
from jinja2 import Environment, FileSystemLoader
import yaml
import shaker


@scenario.configure(context={"cleanup@openstack": ["nova"]},
                    name="InspurPlugin.shaker_test",
                    platform="openstack")
class ShakerTest(utils.NovaScenario):
    """shaker wrapper"""

    TEMPLATE_PATH = '%s/scenarios/shaker/scenarios/openstack'

    def setup_env(self, **kwargs):
        """
        setup environment variables
        :param kwargs:
        :return:
        """
        context = self.context['admin']['credential']
        os.environ['OS_USERNAME'] = context.get('username')
        os.environ['OS_PASSWORD'] = context.get('password')
        os.environ['OS_CACERT'] = context.get('https_cacert')
        os.environ['OS_INSECURE'] = 'True'
        os.environ['OS_REGION_NAME'] = context.get('region_name')
        os.environ['OS_AUTH_URL'] = context.get('auth_url')

        if kwargs.get('external_net'):
            os.environ['SHAKER_EXTERNAL_NET'] = kwargs.get('external_net')

    @staticmethod
    def execute_cmd(cmd):
        from subprocess import Popen, PIPE
        ps = Popen(cmd, stdout=PIPE, universal_newlines=True)
        for stdout_line in iter(ps.stdout.readline, ""):
            print(stdout_line.strip('\n'))
        ps.stdout.close()
        return_code = ps.wait()
        return return_code

    def run(self, zones=list(), scenario=None, endpoint=None, **kwargs):
        """
        run shaker test
        :param zones: availability zones
        :param scenario: scenarios
        :param kwargs: extra parameters
        :return:
        """

        self.setup_env(**kwargs)

        context = self.context
        print(context)

        accommodation = ['pair', 'single_room']

        if not scenario or not endpoint:
            print('scenario/endpoint may not be none')
            return

        module_folder = os.path.dirname(rally_inspur.__file__)
        template_path = ShakerTest.TEMPLATE_PATH % module_folder

        if not os.path.exists(template_path):
            print('file does not exist')
            return

        if len(zones) > 0:
            accommodation.append({
              "zones": zones
            })

        env = Environment(loader=FileSystemLoader(template_path))
        template = env.get_template('%s.yaml.jinja' % scenario)
        output_from_parsed_template = template.render(accommodation=yaml.safe_dump(accommodation))
        print(output_from_parsed_template)

        #shaker_scenario_file_path = "%s/scenarios/openstack/%s.yaml" % (os.path.dirname(shaker.__file__), scenario)

        #with open(shaker_scenario_file_path, 'w') as f:
        #    f.write(output_from_parsed_template)

        # cmd = ['shaker', '--server-endpoint', endpoint, '--scenario', 'openstack/%s' % scenario]
        # code = ShakerTest.execute_cmd(cmd)








