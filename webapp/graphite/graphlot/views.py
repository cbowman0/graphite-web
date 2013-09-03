import re
import math

from django.shortcuts import render_to_response
from django.http import Http404
from django.conf import settings

from graphite.account.models import Profile
from graphite.compat import HttpResponse, HttpResponseBadRequest
from graphite.logger import log
from graphite.util import json
from graphite.user_util import getProfile, getProfileByUsername
from graphite.render.views import parseOptions, config
from graphite.render.evaluator import evaluateTarget
from graphite.storage import STORE

def graphlot_render(request, dest="graphlot.html"):
    """Render the main graphlot view."""
    metrics = []
    for target in request.GET.getlist('target'):
        metrics.append(dict(name=target, yaxis="one"))
    for target in request.GET.getlist('y2target'):
        metrics.append(dict(name=target, yaxis="two"))

    untiltime = request.GET.get('until', "-0hour")
    fromtime = request.GET.get('from', "-24hour")
    events = request.GET.get('events', "")
    width = request.GET.get('width', "300")
    height = request.GET.get('height', "200")
    title = request.GET.get('title', "")
    context = {
      'metric_list' : metrics,
      'fromtime' : fromtime,
      'untiltime' : untiltime,
      'events' : events,
      'height' : height,
      'width' : width,
      'title' : title,
    }
    return render_to_response(dest, context)

def graphlot_render_graph(request):
    return graphlot_render(request, "graphlot_graph.html")

def get_data(request):
    """Get the data for one series."""
    (graphOptions, requestOptions) = parseOptions(request)
    xrange = request.GET.get('xrange', None)
    requestContext = {
        'config' : config,
        'startTime' : requestOptions['startTime'],
        'endTime' : requestOptions['endTime'],
        'localOnly' : False,
        'data' : []
    }
    target = requestOptions['targets'][0]
    seriesList = evaluateTarget(requestContext, target)
    result = []
    for timeseries in seriesList:
#        pointsPerPixel=1
#        if xrange is not None and xrange is not "null":
#            numberOfDataPoints = len(timeseries)
#            pointsPerPixel = math.ceil( float(numberOfDataPoints) / float(xrange) )
#            if pointsPerPixel:
#                timeseries.consolidate(pointsPerPixel)
        result.append(dict(
            name=timeseries.name,
            data=[ x for x in timeseries ],
            start=timeseries.start,
            end=timeseries.end,
#            step=(timeseries.step * pointsPerPixel),
            step=timeseries.step,
            stack=getattr(timeseries, 'stacked', None),
            ))
    if not result:
        raise Exception, "No data for %s" % target
    return HttpResponse(json.dumps(result), mimetype="application/json")


def find_metric(request):
    """Autocomplete helper on metric names."""
    try:
        query = str( request.REQUEST['q'] )
    except:
        return HttpResponseBadRequest(
            content="Missing required parameter 'q'", content_type="text/plain")

    matches = list( STORE.find(query+"*") )
    content = "\n".join([node.path for node in matches ])
    response = HttpResponse(content, content_type='text/plain')

    return response

def header(request):
  "View for the header frame of the browser UI"
  context = {
    'user' : request.user,
    'profile' : getProfile(request),
    'documentation_url' : settings.DOCUMENTATION_URL,
  }
  return render_to_response("browserHeader.html", context)


def browser(request):
  "View for the top-level frame of the browser UI"
  context = {
    'queryString' : request.GET.urlencode(),
    'target' : request.GET.get('target'),
  }
  if context['queryString']:
    context['queryString'] = context['queryString'].replace('#','%23')
  if context['target']:
    context['target'] = context['target'].replace('#','%23') #js libs terminate a querystring on #
  return render_to_response("browser.html", context)


def search(request):
  query = request.POST['query']
  if not query:
    return HttpResponse("")

  patterns = query.split()
  regexes = [re.compile(p,re.I) for p in patterns]
  def matches(s):
    for regex in regexes:
      if regex.search(s):
        return True
    return False

  results = []

  index_file = open(settings.INDEX_FILE)
  for line in index_file:
    if matches(line):
      results.append( line.strip() )
    if len(results) >= 100:
      break

  index_file.close()
  result_string = ','.join(results)
  return HttpResponse(result_string, content_type='text/plain')


def myGraphLookup(request):
  "View for My Graphs navigation"
  profile = getProfile(request,allowDefault=False)
  assert profile

  nodes = []
  leafNode = {
    'allowChildren' : 0,
    'expandable' : 0,
    'leaf' : 1,
  }
  branchNode = {
    'allowChildren' : 1,
    'expandable' : 1,
    'leaf' : 0,
  }

  try:
    path = str( request.GET['path'] )

    if path:
      if path.endswith('.'):
        userpath_prefix = path

      else:
        userpath_prefix = path + '.'

    else:
      userpath_prefix = ""

    matches = [ graph for graph in profile.mygraph_set.all().order_by('name') if graph.name.startswith(userpath_prefix) ]

    log.info( "myGraphLookup: username=%s, path=%s, userpath_prefix=%s, %ld graph to process" % (profile.user.username, path, userpath_prefix, len(matches)) )
    branch_inserted = set()
    leaf_inserted = set()

    for graph in matches: #Now let's add the matching graph
      isBranch = False
      dotPos = graph.name.find( '.', len(userpath_prefix) )

      if dotPos >= 0:
        isBranch = True
        name = graph.name[ len(userpath_prefix) : dotPos ]
        if name in branch_inserted: continue
        branch_inserted.add(name)

      else:
         name = graph.name[ len(userpath_prefix): ]
         if name in leaf_inserted: continue
         leaf_inserted.add(name)

      node = {'text' : str(name) }

      if isBranch:
        node.update( { 'id' : str(userpath_prefix + name + '.') } )
        node.update(branchNode)

      else:
        node.update( { 'id' : str(userpath_prefix + name), 'graphUrl' : str(graph.url) } )
        node.update(leafNode)

      nodes.append(node)

  except:
    log.exception("browser.views.myGraphLookup(): could not complete request.")

  if not nodes:
    no_graphs = { 'text' : "No saved graphs", 'id' : 'no-click' }
    no_graphs.update(leafNode)
    nodes.append(no_graphs)

  return json_response(nodes, request)

def userGraphLookup(request):
  "View for User Graphs navigation"
  username = request.GET['path']
  nodes = []

  branchNode = {
    'allowChildren' : 1,
    'expandable' : 1,
    'leaf' : 0,
  }
  leafNode = {
    'allowChildren' : 0,
    'expandable' : 0,
    'leaf' : 1,
  }

  try:

    if not username:
      profiles = Profile.objects.exclude(user__username='default')

      for profile in profiles:
        if profile.mygraph_set.count():
          node = {
            'text' : str(profile.user.username),
            'id' : str(profile.user.username)
          }

          node.update(branchNode)
          nodes.append(node)

    else:
      profile = getProfileByUsername(username)
      assert profile, "No profile for username '%s'" % username

      for graph in profile.mygraph_set.all().order_by('name'):
        node = {
          'text' : str(graph.name),
          'id' : str(graph.name),
          'graphUrl' : str(graph.url)
        }
        node.update(leafNode)
        nodes.append(node)

  except:
    log.exception("browser.views.userLookup(): could not complete request for %s" % username)

  if not nodes:
    no_graphs = { 'text' : "No saved graphs", 'id' : 'no-click' }
    no_graphs.update(leafNode)
    nodes.append(no_graphs)

  return json_response(nodes, request)


def json_response(nodes, request=None):
  if request:
    jsonp = request.REQUEST.get('jsonp', False)
  else:
    jsonp = False
  json_data = json.dumps(nodes)
  if jsonp:
    response = HttpResponse("%s(%s)" % (jsonp, json_data),
                            content_type="text/javascript")
  else:
    response = HttpResponse(json_data, content_type="application/json")
  response['Pragma'] = 'no-cache'
  response['Cache-Control'] = 'no-cache'
  return response
