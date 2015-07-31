#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
import os
import testtools
import yaml

from heatclient.v1 import events
from heatclient.v1 import resources
from heatclient.v1 import stacks

from heat_vis import render


class RenderTest(testtools.TestCase):

    def noop(self):
        pass

    def setUp(self):
        super(RenderTest, self).setUp()
        self.render = render.StackRender()
        self.path = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                 'data')
        with open('%s/%s' % (self.path, 'test-stack.yaml')) as f:
            self.render.stack = stacks.Stack(None, yaml.safe_load(f)['stack'])
        with open('%s/%s' % (self.path, 'test-stacks.yaml')) as f:
            self.render.stacks = [stacks.Stack(None, s)
                                  for s in yaml.safe_load(f)]
        with open('%s/%s' % (self.path, 'test-events-create.yaml')) as f:
            self.render.events = [events.Event(None, e)
                                  for e in yaml.safe_load(f)]
        with open('%s/%s' % (self.path, 'test-resources.yaml')) as f:
            self.render.resources = [resources.Resource(None, r)
                                     for r in yaml.safe_load(f)]

    def test_render_event_chart(self):
        print(self.render.render_event_chart())


if __name__ == "__main__":
    rt = RenderTest(methodName='noop')
    rt.setUp()
    rt.test_render_event_chart()
