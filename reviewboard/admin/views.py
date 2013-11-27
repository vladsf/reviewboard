from __future__ import unicode_literals

import json
import logging

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.template.loader import render_to_string
from django.utils.translation import ugettext as _
from djblets.siteconfig.models import SiteConfiguration
from djblets.siteconfig.views import site_settings as djblets_site_settings

from reviewboard.admin.cache_stats import get_cache_stats
from reviewboard.admin.forms import SSHSettingsForm
from reviewboard.admin.support import get_support_url
from reviewboard.admin.widgets import (dynamic_activity_data,
                                       primary_widgets,
                                       secondary_widgets)
from reviewboard.ssh.client import SSHClient
from reviewboard.ssh.utils import humanize_key


@staff_member_required
def dashboard(request, template_name="admin/dashboard.html"):
    """
    Displays the administration dashboard, containing news updates and
    useful administration tasks.
    """
    return render_to_response(template_name, RequestContext(request, {
        'title': _("Admin Dashboard"),
        'root_path': settings.SITE_ROOT + "admin/db/",
        'primary_widgets': primary_widgets,
        'secondary_widgets': secondary_widgets,
    }))


@staff_member_required
def cache_stats(request, template_name="admin/cache_stats.html"):
    """
    Displays statistics on the cache. This includes such pieces of
    information as memory used, cache misses, and uptime.
    """
    cache_stats = get_cache_stats()

    return render_to_response(template_name, RequestContext(request, {
        'cache_hosts': cache_stats,
        'cache_backend': settings.CACHES['default']['BACKEND'],
        'title': _("Server Cache"),
        'root_path': settings.SITE_ROOT + "admin/db/"
    }))


@staff_member_required
def site_settings(request, form_class,
                  template_name="siteconfig/settings.html"):
    return djblets_site_settings(request, form_class, template_name, {
        'root_path': settings.SITE_ROOT + "admin/db/"
    })


@staff_member_required
def ssh_settings(request, template_name='admin/ssh_settings.html'):
    client = SSHClient()
    key = client.get_user_key()

    if request.method == 'POST':
        form = SSHSettingsForm(request.POST, request.FILES)

        if form.is_valid():
            if form.did_request_delete() and client.get_user_key() is not None:
                try:
                    form.delete()
                    return HttpResponseRedirect('.')
                except Exception as e:
                    logging.error('Deleting SSH key failed: %s' % e)
            else:
                try:
                    form.create(request.FILES)
                    return HttpResponseRedirect('.')
                except Exception as e:
                    # Fall through. It will be reported inline and in the log.
                    logging.error('Uploading SSH key failed: %s' % e)
    else:
        form = SSHSettingsForm()

    if key:
        fingerprint = humanize_key(key)
    else:
        fingerprint = None

    return render_to_response(template_name, RequestContext(request, {
        'key': key,
        'fingerprint': fingerprint,
        'public_key': client.get_public_key(key),
        'form': form,
    }))


def manual_updates_required(
        request, updates,
        template_name="admin/manual_updates_required.html"):
    """
    Checks for required manual updates and displays informational pages on
    performing the necessary updates.
    """
    return render_to_response(template_name, RequestContext(request, {
        'updates': [render_to_string(template_name,
                                     RequestContext(request, extra_context))
                    for (template_name, extra_context) in updates],
    }))


def widget_toggle(request):
    """
    Controls the state of widgets - collapsed or expanded.
    Saves the state into site settings.
    """
    collapsed = request.GET.get('collapse', None)
    widget = request.GET.get('widget', None)

    if widget and collapsed:
        siteconfig = SiteConfiguration.objects.get_current()
        widget_settings = siteconfig.get("widget_settings", {})

        widget_settings[widget] = collapsed
        siteconfig.set("widget_settings", widget_settings)
        siteconfig.save()

    return HttpResponse("")


def widget_activity(request):
    """
    Receives an AJAX request, sends the data to the widget controller and
    returns JSON data
    """
    activity_data = dynamic_activity_data(request)

    return HttpResponse(json.dumps(activity_data),
                        mimetype="application/json")


def support_redirect(request):
    """Redirects to the Beanbag support page for Review Board."""
    return HttpResponseRedirect(get_support_url(request))
