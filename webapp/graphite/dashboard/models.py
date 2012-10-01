from django.db import models
from django.contrib.auth import models as auth_models
from graphite.account.models import Profile
from graphite.util import json

import re

class Dashboard(models.Model):
  class Admin: pass
  name = models.CharField(primary_key=True, max_length=128)
  owners = models.ManyToManyField(Profile, related_name='dashboards')
  state = models.TextField()
  __str__ = lambda self: "Dashboard [%s]" % self.name


class Template(models.Model):
  metric_path_re = re.compile(r'([^.()]+\.){5}')

  class Admin: pass
  name = models.CharField(primary_key=True, max_length=128)
  owners = models.ManyToManyField(Profile, related_name='templates')
  state = models.TextField()
  __str__ = lambda self: "Template [%s]" % self.name

  def loadState(self, host_id):
    return self.state.replace('__HOST_ID__', host_id)

  def setState(self, state):
    def replace_hostid(s):
      if isinstance(s, unicode):
        s = self.__class__.metric_path_re.sub('__HOST_ID__.', s)
      return s

    def update_graph(graph):
      graph_opts = graph[1]
      graph_opts['target'] = [replace_hostid(s) for s in graph_opts['target']]
      return [replace_hostid(graph[0]),
              graph_opts,
              replace_hostid(graph[2])]

    # Parse JSON here and replace first five elements of target with __HOST_ID__
    parsed_state = json.loads(state)
    for i, graph in enumerate(parsed_state['graphs']):
      parsed_state['graphs'][i] = update_graph(graph)
    self.state = json.dumps(parsed_state)
