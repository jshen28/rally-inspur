from rally_inspur.scenarios.utils.basic_ha import BasicNovaHa
from rally.task import types
from rally.task import validation

from rally_openstack import consts
from rally_openstack import scenario


@types.convert(image={"type": "glance_image"},
               flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor", flavor_param="flavor",
                image_param="image")
@validation.add("required_services", services=[consts.Service.NOVA])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["nova"]},
                    name="InspurPlugin.keepalived_ha",
                    platform="openstack")
class KeepalivedHa(BasicNovaHa):

    def run(self, image, flavor, hosts=list(['msg01', 'msg02', 'msg03']), salt_passwd=None, salt_api_url=None, **kwargs):
        kwargs.update({
            "image": image,
            "flavor": flavor,
            "hosts": hosts,
            "cmd": 'systemctl stop keepalived',
            'restore': 'systemctl start keepalived'
        })
        self._run(salt_api_uri=salt_api_url, salt_user_passwd=salt_passwd, **kwargs)
