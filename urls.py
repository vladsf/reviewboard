from django.conf import settings
from django.conf.urls.defaults import *
from reviewboard.reviews.models import ReviewRequest, Group
from reviewboard.reviews.feeds import RssReviewsFeed, AtomReviewsFeed
from reviewboard.reviews.feeds import RssSubmitterReviewsFeed
from reviewboard.reviews.feeds import AtomSubmitterReviewsFeed
from reviewboard.reviews.feeds import RssGroupReviewsFeed
from reviewboard.reviews.feeds import AtomGroupReviewsFeed
import os.path

rss_feeds = {
    'reviews': RssReviewsFeed,
    'users': RssSubmitterReviewsFeed,
    'groups': RssGroupReviewsFeed,
}

atom_feeds = {
    'reviews': AtomReviewsFeed,
    'users': AtomSubmitterReviewsFeed,
    'groups': AtomGroupReviewsFeed,
}

urlpatterns = patterns('',
    (r'^admin/', include('django.contrib.admin.urls')),

    (r'^$', 'django.views.generic.simple.redirect_to',
     {'url': '/reviews/'}),

    # Review request browsing
    (r'^reviews/$', 'reviewboard.reviews.views.dashboard',
     {'template_name': 'reviews/dashboard.html'}),

    (r'^reviews/all/$', 'reviewboard.reviews.views.review_list',
     {'queryset': ReviewRequest.objects.filter(public=True, status='P'),
      'template_name': 'reviews/review_list.html'}),

    # Review request creation
    (r'^reviews/new/changenum/$',
      'reviewboard.reviews.views.new_from_changenum'),
    (r'^reviews/new/$', 'reviewboard.reviews.views.new_review_request'),

    # Review request detail
    (r'^reviews/(?P<object_id>[0-9]+)/$',
     'reviewboard.reviews.views.review_detail',
     {'template_name': 'reviews/review_detail.html'}),

    # Review request diffs
    (r'^reviews/(?P<object_id>[0-9]+)/diff/$',
     'reviewboard.reviews.views.diff'),
    (r'^reviews/(?P<object_id>[0-9]+)/diff/(?P<revision>[0-9]+)/$',
     'reviewboard.reviews.views.diff'),

    (r'^reviews/(?P<object_id>[0-9]+)/diff/(?P<revision>[0-9]+)/fragment/(?P<filediff_id>[0-9]+)/$',
     'reviewboard.reviews.views.diff_fragment'),

    # Review request drafts
    (r'^reviews/(?P<object_id>[0-9]+)/draft/save/$',
     'reviewboard.reviews.views.save_draft'),
    (r'^reviews/(?P<object_id>[0-9]+)/draft/revert/$',
     'reviewboard.reviews.views.revert_draft'),

    # Review request modification
    (r'^reviews/(?P<object_id>[0-9]+)/edit/$',
      'django.views.generic.create_update.update_object',
     {'model': ReviewRequest,
      'template_name': 'reviews/edit_details.html'}),

    (r'^reviews/[0-9]+/diff/upload/$',
     'reviewboard.diffviewer.views.upload',
      {'donepath': 'done/%s/'}),

    (r'^reviews/(?P<review_request_id>[0-9]+)/diff/upload/done/(?P<diffset_id>[0-9]+)/$',
     'reviewboard.reviews.views.upload_diff_done'),

    (r'^reviews/(?P<review_request_id>[0-9]+)/publish/$',
     'reviewboard.reviews.views.publish'),

    (r'^reviews/(?P<review_request_id>[0-9]+)/(?P<action>(discard|submitted|reopen))/$',
     'reviewboard.reviews.views.setstatus'),

    # Review request replies
    (r'^reviews/(?P<review_request_id>[0-9]+)/replies/(?P<revision>[0-9]+)/comments/$',
     'reviewboard.reviews.views.reply_comments'),

    (r'^reviews/(?P<review_request_id>[0-9]+)/replies/(?P<revision>[0-9]+)/save/$',
     'reviewboard.reviews.views.reply_save'),

    (r'^reviews/(?P<review_request_id>[0-9]+)/replies/(?P<revision>[0-9]+)/delete/$',
     'reviewboard.reviews.views.reply_delete'),

    (r'^reviews/(?P<review_request_id>[0-9]+)/replies/(?P<revision>[0-9]+)/publish/$',
     'reviewboard.reviews.views.reply_publish'),

    # Review replies
    (r'^reviews/(?P<review_request_id>[0-9]+)/reply/$',
     'reviewboard.reviews.views.review_reply'),
    (r'^reviews/(?P<review_request_id>[0-9]+)/reply/(?P<review_id>[0-9]+)/save/$',
     'reviewboard.reviews.views.review_reply_save'),
    (r'^reviews/(?P<review_request_id>[0-9]+)/reply/(?P<review_id>[0-9]+)/discard/$',
     'reviewboard.reviews.views.review_reply_discard'),

    # Review request JSON/XML handlers
    (r'^reviews/(?P<review_request_id>[0-9]+)/(?P<method>(json|xml))/(?P<field_name>[A-Za-z0-9_-]+)/$',
     'reviewboard.reviews.views.review_request_field'),

    (r'^reviews/(?P<review_request_id>[0-9]+)/(?P<method>(json|xml))/$',
     'reviewboard.reviews.views.review_request_field'),

    # E-mail previews
    (r'^reviews/(?P<review_request_id>[0-9]+)/preview-email/$',
     'reviewboard.reviews.views.preview_review_request_email'),
    (r'^reviews/(?P<review_request_id>[0-9]+)/replies/preview-email/(?P<review_id>[0-9]+)/$',
     'reviewboard.reviews.views.preview_reply_email'),

    # Comments
    (r'^reviews/(?P<review_request_id>[0-9]+)/diff/comments/(?P<filediff_id>[0-9]+)/(?P<line>[0-9]+)/$',
     'reviewboard.reviews.views.comments'),
    (r'^reviews/(?P<review_request_id>[0-9]+)/diff/(?P<revision>[0-9]+)/comments/(?P<filediff_id>[0-9]+)/(?P<line>[0-9]+)/$',
     'reviewboard.reviews.views.comments'),

    # Users
    (r'^users/$', 'reviewboard.reviews.views.submitter_list',
     {'template_name': 'reviews/submitter_list.html'}),

    (r'^users/(?P<username>[A-Za-z0-9_-]+)/$',
     'reviewboard.reviews.views.submitter',
     {'template_name': 'reviews/review_list.html'}),

    # Groups
    (r'^groups/$', 'reviewboard.reviews.views.group_list',
     {'template_name': 'reviews/group_list.html'}),

    (r'^groups/(?P<name>[A-Za-z0-9_-]+)/$',
     'reviewboard.reviews.views.group',
     {'template_name': 'reviews/review_list.html'}),

    # Feeds
    (r'^feeds/rss/(?P<url>.*)/$', 'django.contrib.syndication.views.feed',
     {'feed_dict': rss_feeds}),
    (r'^feeds/atom/(?P<url>.*)/$', 'django.contrib.syndication.views.feed',
     {'feed_dict': atom_feeds}),

    # Authentication and accounts
    (r'^account/login/$', 'djblets.auth.views.login',
     {'next_page': '/reviews/'}),
    (r'^account/logout/$', 'django.contrib.auth.views.logout',
     {'next_page': settings.LOGIN_URL}),
    (r'^account/preferences/$', 'reviewboard.accounts.views.user_preferences',),
)

if settings.BUILTIN_AUTH:
    urlpatterns += patterns('',
        (r'^account/register/$', 'djblets.auth.views.register',
         {'next_page': '/reviews/'}),
    )

# Add static media if running in DEBUG mode
if settings.DEBUG:
    def htdocs_path(leaf):
        return os.path.join(settings.HTDOCS_ROOT, leaf)

    urlpatterns += patterns('',
        (r'^css/(?P<path>.*)$', 'django.views.static.serve', {
            'show_indexes': True,
            'document_root': htdocs_path('css'),
            }),
        (r'^images/(?P<path>.*)$', 'django.views.static.serve', {
            'show_indexes': True,
            'document_root': htdocs_path('images'),
            }),
        (r'^scripts/(?P<path>.*)$', 'django.views.static.serve', {
            'show_indexes': True,
            'document_root': htdocs_path('scripts')
            }),
    )
