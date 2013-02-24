from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, HttpResponsePermanentRedirect

from url_shortener.baseconv import base62
from url_shortener.models import Link
import re

def follow(request, link_id):
    """Follow existing links"""
    key = base62.to_decimal(link_id)
    link = get_object_or_404(Link, pk=key)
    return HttpResponsePermanentRedirect('/' + link.url)

def shorten(request, path):
    if request.META.get('QUERY_STRING', None):
        path += '?' + request.META['QUERY_STRING']
    # Remove _salt and _dc to avoid creating many copies of the same URL
    path = re.sub('&_(salt|dc)=[0-9.]+', "", path)

    link, created = Link.objects.get_or_create(url=path)
    link_id = base62.from_decimal(link.id)
    url = reverse('graphite.url_shortener.views.follow', kwargs={'link_id': link_id})
    return HttpResponse("Your short link is <a href=\"%s\">%s</a>" % (url, url))
