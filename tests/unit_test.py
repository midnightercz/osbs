from __future__ import absolute_import, unicode_literals
import copy
import inspect
import json
import os

import pytest
import logging
from .fake_api import openshift
from osbs.build import DockJsonManipulator, BuildManager
from tests.constants import TEST_BUILD, TEST_LABEL, TEST_LABEL_VALUE


logger = logging.getLogger("osbs.tests")


def test_set_labels_on_build(openshift):
    l = openshift.set_labels_on_build(TEST_BUILD, {TEST_LABEL: TEST_LABEL_VALUE})
    assert l.json() is not None


def test_get_oauth_token(openshift):
    token = openshift.get_oauth_token()
    assert token is not None


def test_list_builds(openshift):
    l = openshift.list_builds()
    assert l is not None
    assert bool(l.json())  # is there at least something



#####
#
# build/DockJsonManipulator
#
#####

BUILD_JSON = {
    "metadata": {
        "name": "{{NAME}}"
    },
    "kind": "Build",
    "apiVersion": "v1beta1",
    "parameters": {
        "source": {
            "type": "Git",
            "git": {
                "uri": "{{GIT_URI}}"
            }
        },
        "strategy": {
            "type": "Custom",
            "customStrategy": {
                "image": "buildroot",
                "exposeDockerSocket": True,
                "env": [{
                    "name": "DOCK_PLUGINS",
                    "value": "TBD"
                }]
            }
        },
        "output": {
            "imageTag": "{{OUTPUT_IMAGE_TAG}}",
            "registry": "{{REGISTRY_URI}}"
        }
    }
}

INNER_DOCK_JSON = {
    "prebuild_plugins": [
        {
            "name": "change_from_in_dockerfile"
        },
        {
            "args": {
                "key1": {
                    "a": "1",
                    "b": "2"
                },
                "key2": "b"
            },
            "name": "a_plugin"
        },
    ],
    "postbuild_plugins": [
        {
            "args": {
                "image_id": "BUILT_IMAGE_ID"
            },
            "name": "all_rpm_packages"
        },
    ]
}


def test_manipulator():
    m = DockJsonManipulator(BUILD_JSON, INNER_DOCK_JSON)
    assert m is not None

    
def test_manipulator_get_dock_json():
    build_json = copy.deepcopy(BUILD_JSON)
    env_json = build_json['parameters']['strategy']['customStrategy']['env']
    p = [env for env in env_json if env["name"] == "DOCK_PLUGINS"]
    inner = {
        "a": "b"
    }
    p[0]['value'] = json.dumps(inner)
    m = DockJsonManipulator(build_json, None)
    response = m.get_dock_json()
    assert response["a"] == inner["a"]


def test_manipulator_get_dock_json_missing_input():
    build_json = copy.deepcopy(BUILD_JSON)
    build_json['parameters']['strategy']['customStrategy']['env'] = None
    m = DockJsonManipulator(build_json, None)
    with pytest.raises(RuntimeError):
        m.get_dock_json()


def test_manipulator_merge():
    inner = copy.deepcopy(INNER_DOCK_JSON)
    plugin = [x for x in inner['prebuild_plugins'] if x["name"] == "a_plugin"][0]
    m = DockJsonManipulator(None, inner)
    m.dock_json_merge_arg("prebuild_plugins", "a_plugin", "key1", {"a": '3', "z": '9'})
    assert plugin['args']['key1']['a'] == '3'
    assert plugin['args']['key1']['b'] == '2'
    assert plugin['args']['key1']['z'] == '9'


def test_render_prod_request():
    this_file = inspect.getfile(test_render_prod_request)
    this_dir = os.path.dirname(this_file)
    parent_dir = os.path.dirname(this_dir)
    inputs_path = os.path.join(parent_dir, "inputs")
    bm = BuildManager(inputs_path)
    kwargs = {
        'git_uri': "http://git/",
        'git_ref': "master",
        'user': "john-foo",
        'component': "component",
        'registry_uri': "registry.example.com",
        'openshift_uri': "http://openshift/",
        'koji_target': "koji-target",
        'kojiroot': "http://root/",
        'kojihub': "http://hub/",
        'sources_command': "make",
        'architecture': "x86_64",
        'vendor': "Foo Vendor",
        'build_host': "our.build.host.example.com",
        'authoritative_registry': "registry.example.com",
    }
    build = bm.get_build("prod", **kwargs)