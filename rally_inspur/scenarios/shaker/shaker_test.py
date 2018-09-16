from rally_openstack import scenario
from rally_openstack.scenarios.nova import utils
import rally_inspur
import os
from jinja2 import Environment, FileSystemLoader
import yaml
import shaker
import subprocess


@scenario.configure(context={"cleanup@openstack": ["nova"]},
                    name="InspurPlugin.shaker_test",
                    platform="openstack")
class ShakerTest(utils.NovaScenario):
    """shaker wrapper"""

    TEMPLATE_PATH = '%s/scenarios/shaker/scenarios/openstack'

    def run(self, zones=list(), scenario=None, **kwargs):

        context = self.context
        print(context)

        accommodation = ['pair', 'single_pair']

        if not scenario:
            print('scenario may not be none')
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

        # p = subprocess.Popen(['shaker'], stdout=subprocess.PIPE)
        # result, exit_code = p.communicate()








