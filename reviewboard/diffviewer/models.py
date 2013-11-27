from __future__ import unicode_literals

import hashlib
import logging

from django.db import models
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from djblets.db.fields import Base64Field

from reviewboard.diffviewer.managers import FileDiffDataManager, DiffSetManager
from reviewboard.scmtools.core import PRE_CREATION
from reviewboard.scmtools.models import Repository


class FileDiffData(models.Model):
    """
    Contains hash and base64 pairs.

    These pairs are used to reduce diff database storage.
    """
    binary_hash = models.CharField(_("hash"), max_length=40, primary_key=True)
    binary = Base64Field(_("base64"))
    objects = FileDiffDataManager()

    # These are null by default so that we don't get counts of 0 for older
    # changes.
    insert_count = models.IntegerField(null=True, blank=True)
    delete_count = models.IntegerField(null=True, blank=True)

    def recalculate_line_counts(self, tool):
        """Recalculates the insert_count and delete_count values.

        This will attempt to re-parse the stored diff and fetch the
        line counts through the parser.
        """
        logging.debug('Recalculating insert/delete line counts on '
                      'FileDiffData %s' % self.pk)

        files = tool.get_parser(self.binary).parse()

        if len(files) != 1:
            logging.error('Failed to correctly parse stored diff data in '
                          'FileDiffData ID %s when trying to get '
                          'insert/delete line counts' % self.pk)
        else:
            file_info = files[0]
            self.insert_count = file_info.insert_count
            self.delete_count = file_info.delete_count
            self.save()


@python_2_unicode_compatible
class FileDiff(models.Model):
    """
    A diff of a single file.

    This contains the patch and information needed to produce original and
    patched versions of a single file in a repository.
    """
    MODIFIED = 'M'
    MOVED = 'V'
    DELETED = 'D'

    STATUSES = (
        (MODIFIED, _('Modified')),
        (MOVED, _('Moved')),
        (DELETED, _('Deleted')),
    )

    diffset = models.ForeignKey('DiffSet',
                                related_name='files',
                                verbose_name=_("diff set"))

    source_file = models.CharField(_("source file"), max_length=1024)
    dest_file = models.CharField(_("destination file"), max_length=1024)
    source_revision = models.CharField(_("source file revision"),
                                       max_length=512)
    dest_detail = models.CharField(_("destination file details"),
                                   max_length=512)
    diff64 = Base64Field(_("diff"), db_column="diff_base64", blank=True)
    diff_hash = models.ForeignKey('FileDiffData', null=True, blank=True)
    binary = models.BooleanField(_("binary file"), default=False)
    parent_diff64 = Base64Field(_("parent diff"),
                                db_column="parent_diff_base64", blank=True)
    parent_diff_hash = models.ForeignKey('FileDiffData', null=True, blank=True,
                                         related_name='parent_filediff_set')
    status = models.CharField(_("status"), max_length=1, choices=STATUSES)

    @property
    def source_file_display(self):
        tool = self.diffset.repository.get_scmtool()
        return tool.normalize_path_for_display(self.source_file)

    @property
    def dest_file_display(self):
        tool = self.diffset.repository.get_scmtool()
        return tool.normalize_path_for_display(self.dest_file)

    @property
    def deleted(self):
        return self.status == self.DELETED

    @property
    def moved(self):
        return self.status == self.MOVED

    @property
    def is_new(self):
        return self.source_revision == PRE_CREATION

    def _get_diff(self):
        if not self.diff_hash:
            self._migrate_diff_data()

        return self.diff_hash.binary

    def _set_diff(self, diff):
        hashkey = self._hash_hexdigest(diff)

        # Add hash to table if it doesn't exist, and set diff_hash to this.
        self.diff_hash, is_new = FileDiffData.objects.get_or_create(
            binary_hash=hashkey, defaults={'binary': diff})
        self.diff64 = ""

    diff = property(_get_diff, _set_diff)

    def _get_parent_diff(self):
        if self.parent_diff64 and not self.parent_diff_hash:
            self._migrate_diff_data()

        if self.parent_diff_hash:
            return self.parent_diff_hash.binary
        else:
            return None

    def _set_parent_diff(self, parent_diff):
        if parent_diff != "":
            hashkey = self._hash_hexdigest(parent_diff)

            # Add hash to table if it doesn't exist, and set diff_hash to this.
            self.parent_diff_hash, is_new = FileDiffData.objects.get_or_create(
                binary_hash=hashkey, defaults={'binary': parent_diff})
            self.parent_diff64 = ""

    parent_diff = property(_get_parent_diff, _set_parent_diff)

    @property
    def insert_count(self):
        if not self.diff_hash:
            self._migrate_diff_data()

        if self.diff_hash.insert_count is None:
            self._recalculate_line_counts(self.diff_hash)

        return self.diff_hash.insert_count

    @property
    def delete_count(self):
        if not self.diff_hash:
            self._migrate_diff_data()

        if self.diff_hash.delete_count is None:
            self._recalculate_line_counts(self.diff_hash)

        return self.diff_hash.delete_count

    def set_line_counts(self, insert_count, delete_count):
        """Sets the insert/delete line count on the FileDiff."""
        if not self.diff_hash:
            # This really shouldn't happen, but if it does, we should handle
            # it gracefully.
            logging.warning('Attempting to call set_line_counts on '
                            'un-migrated FileDiff %s' % self.pk)
            self._migrate_diff_data(False)

        if (self.diff_hash.insert_count is not None and
                self.diff_hash.insert_count != insert_count):
            logging.warning('Attempting to override insert count on '
                            'FileDiffData %s from %s to %s (FileDiff %s)'
                            % (self.diff_hash.pk,
                               self.diff_hash.insert_count,
                               insert_count,
                               self.pk))

        if (self.diff_hash.delete_count is not None and
                self.diff_hash.delete_count != delete_count):
            logging.warning('Attempting to override delete count on '
                            'FileDiffData %s from %s to %s (FileDiff %s)'
                            % (self.diff_hash.pk,
                               self.diff_hash.delete_count,
                               delete_count,
                               self.pk))

        self.diff_hash.insert_count = insert_count
        self.diff_hash.delete_count = delete_count
        self.diff_hash.save()

    def _hash_hexdigest(self, diff):
        hasher = hashlib.sha1()
        hasher.update(diff)
        return hasher.hexdigest()

    def _migrate_diff_data(self, recalculate_counts=True):
        """Migrates the data stored in the FileDiff to a FileDiffData."""
        needs_save = False

        if not self.diff_hash:
            logging.debug('Migrating FileDiff %s diff data to FileDiffData'
                          % self.pk)
            needs_save = True
            self._set_diff(self.diff64)

            if recalculate_counts:
                self._recalculate_line_counts(self.diff_hash)

        if self.parent_diff64 and not self.parent_diff_hash:
            logging.debug('Migrating FileDiff %s parent_diff data to '
                          'FileDiffData' % self.pk)
            needs_save = True
            self._set_parent_diff(self.parent_diff64)

            if recalculate_counts:
                self._recalculate_line_counts(self.parent_diff_hash)

        if needs_save:
            self.save()

    def _recalculate_line_counts(self, diff_hash):
        """Recalculates the line counts on the specified FileDiffData.

        This requires that diff_hash is set. Otherwise, it will assert.
        """
        diff_hash.recalculate_line_counts(
            self.diffset.repository.get_scmtool())

    def __str__(self):
        return "%s (%s) -> %s (%s)" % (self.source_file, self.source_revision,
                                       self.dest_file, self.dest_detail)


@python_2_unicode_compatible
class DiffSet(models.Model):
    """
    A revisioned collection of FileDiffs.
    """
    name = models.CharField(_('name'), max_length=256)
    revision = models.IntegerField(_("revision"))
    timestamp = models.DateTimeField(_("timestamp"), default=timezone.now)
    basedir = models.CharField(_('base directory'), max_length=256,
                               blank=True, default='')
    history = models.ForeignKey('DiffSetHistory', null=True,
                                related_name="diffsets",
                                verbose_name=_("diff set history"))
    repository = models.ForeignKey(Repository, related_name="diffsets",
                                   verbose_name=_("repository"))
    diffcompat = models.IntegerField(
        _('differ compatibility version'),
        default=0,
        help_text=_("The diff generator compatibility version to use. "
                    "This can and should be ignored."))

    base_commit_id = models.CharField(
        _('commit ID'), max_length=64, blank=True, null=True, db_index=True,
        help_text=_('The ID/revision this change is built upon.'))

    objects = DiffSetManager()

    def save(self, **kwargs):
        """
        Saves this diffset.

        This will set an initial revision of 1 if this is the first diffset
        in the history, and will set it to on more than the most recent
        diffset otherwise.
        """
        if self.revision == 0 and self.history is not None:
            if self.history.diffsets.count() == 0:
                # Start on revision 1. It's more human-grokable.
                self.revision = 1
            else:
                self.revision = self.history.diffsets.latest().revision + 1

        if self.history:
            self.history.last_diff_updated = self.timestamp
            self.history.save()

        super(DiffSet, self).save()

    def __str__(self):
        return "[%s] %s r%s" % (self.id, self.name, self.revision)

    class Meta:
        get_latest_by = 'revision'
        ordering = ['revision', 'timestamp']


@python_2_unicode_compatible
class DiffSetHistory(models.Model):
    """
    A collection of diffsets.

    This gives us a way to store and keep track of multiple revisions of
    diffsets belonging to an object.
    """
    name = models.CharField(_('name'), max_length=256)
    timestamp = models.DateTimeField(_("timestamp"), default=timezone.now)
    last_diff_updated = models.DateTimeField(
        _("last updated"),
        blank=True,
        null=True,
        default=None)

    def __str__(self):
        return 'Diff Set History (%s revisions)' % self.diffsets.count()

    class Meta:
        verbose_name_plural = "Diff set histories"
