# -*- coding: ascii -*-
#  ______ _ _      _____            _       _____ _ _            _
# |  ____(_) |    |  __ \          | |     / ____| (_)          | |
# | |__   _| | ___| |__) |___   ___| | __ | |    | |_  ___ _ __ | |_
# |  __| | | |/ _ \  _  // _ \ / __| |/ / | |    | | |/ _ \ '_ \| __|
# | |    | | |  __/ | \ \ (_) | (__|   <  | |____| | |  __/ | | | |_
# |_|    |_|_|\___|_|  \_\___/ \___|_|\_\  \_____|_|_|\___|_| |_|\__|
#
# Copyright (C) 2012 Heyware s.r.l.
#
# This file is part of FileRock Client.
#
# FileRock Client is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# FileRock Client is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with FileRock Client. If not, see <http://www.gnu.org/licenses/>.
#

"""
This is the filesystemwatcher_test module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

from nose.tools import *
from filerockclient.filesystemwatcher.FileSystemWatcherCrossPlatform import WareboxSnapshot
import random


def test_split_preservers_all_pathnames():
    snapshot = create_snapshot_with_different_filesizes()
    num_of_pathnames = len(snapshot.pathnames)
    snapshot._split_on_sizes = [0, 10, 100, 1000]
    chunks = snapshot.split_by_size()
    num_of_pathnames_after = sum(map(lambda x: len(x.pathnames), chunks))
    assert_equal(num_of_pathnames, num_of_pathnames_after)


def test_split_produces_correct_num_of_chunks():
    snapshot = create_snapshot_with_different_filesizes()
    snapshot._split_on_sizes = [0, 10, 100, 1000]
    chunks = snapshot.split_by_size()
    assert_equal(len(chunks), 4)


def test_split_doesnt_produce_empty_chunks():
    snapshot = create_snapshot_with_different_filesizes()
    # Note: the [80..90) class is empty
    snapshot._split_on_sizes = [0, 10, 80, 90, 100, 1000]
    chunks = snapshot.split_by_size()
    assert_equal(len(chunks), 5)


def test_split_produces_consistent_chunks():
    snapshot = create_snapshot_with_different_filesizes()
    snapshot._split_on_sizes = [0, 10, 100, 1000]
    chunks = snapshot.split_by_size()
    limits = (0, 10, 100, 1000, float('inf'))
    for i, chunk in enumerate(chunks):
        lower = limits[i]
        upper = limits[i + 1]
        for pathname in chunk.pathnames:
            assert_true(lower <= chunk.metadata[pathname]['size'] < upper)


def test_pathname_creations_are_detected():
    snapshot1 = create_snapshot_before_modification()
    snapshot2 = create_snapshot_after_modification()
    created_pathnames, _, _ = snapshot2.detect_modifications_from(snapshot1)
    assert_equal(len(created_pathnames), 1)
    assert_equal(created_pathnames[0], 'file0.txt')


def test_pathname_modifications_are_detected():
    snapshot1 = create_snapshot_before_modification()
    snapshot2 = create_snapshot_after_modification()
    _, modified_pathnames, _ = snapshot2.detect_modifications_from(snapshot1)
    assert_equal(len(modified_pathnames), 3)
    assert_in('file2.txt', modified_pathnames)
    assert_in('file3.txt', modified_pathnames)
    assert_in('file4.txt', modified_pathnames)


def test_pathname_copies_are_detected():
    snapshot1 = create_snapshot_before_modification()
    snapshot2 = create_snapshot_after_modification()
    _, _, copied_pathnames = snapshot2.detect_modifications_from(snapshot1)
    assert_equal(len(copied_pathnames), 6)
    copied_pathnames_ = dict(copied_pathnames)
    assert_in('file5.txt', copied_pathnames_)
    assert_in('file7.txt', copied_pathnames_)
    assert_in('file8.txt', copied_pathnames_)
    assert_in('file9.txt', copied_pathnames_)
    assert_in('fileA.txt', copied_pathnames_)
    assert_in('fileB.txt', copied_pathnames_)


def test_pathname_deletions_are_detected():
    snapshot1 = create_snapshot_before_modification()
    snapshot2 = create_snapshot_after_modification()
    deleted_pathnames = snapshot2.detect_deletions_from(snapshot1)
    assert_equal(len(deleted_pathnames), 2)
    assert_in('file6.txt', deleted_pathnames)
    assert_in('fileC.txt', deleted_pathnames)


def test_folders_are_not_copied():
    snapshot1 = create_snapshot_with_hierarchy_before_modification()
    snapshot2 = create_snapshot_with_hierarchy_after_modification()
    created_pathnames, _, _ = snapshot2.detect_modifications_from(snapshot1)
    assert_in('folder2/', created_pathnames)
    assert_in('folder3/', created_pathnames)
    assert_in('folder4/', created_pathnames)


def test_small_files_are_not_copied():
    snapshot1 = create_snapshot_with_hierarchy_before_modification()
    snapshot2 = create_snapshot_with_hierarchy_after_modification()
    first_copied_file =  ('folder3/file.txt', 'folder1/file.txt')  # size 2
    second_copied_file = ('folder4/file.txt', 'folder2/file.txt')  # size 3

    snapshot2._dont_copy_below_size = 2
    _, _, copied_pathnames = snapshot2.detect_modifications_from(snapshot1)
    assert_in(first_copied_file, copied_pathnames)
    assert_in(second_copied_file, copied_pathnames)

    snapshot2._dont_copy_below_size = 3
    _, _, copied_pathnames = snapshot2.detect_modifications_from(snapshot1)
    assert_not_in(first_copied_file, copied_pathnames)
    assert_in(second_copied_file, copied_pathnames)

    snapshot2._dont_copy_below_size = 4
    _, _, copied_pathnames = snapshot2.detect_modifications_from(snapshot1)
    assert_not_in(first_copied_file, copied_pathnames)
    assert_not_in(second_copied_file, copied_pathnames)


def test_pathnames_are_created_after_their_parents():
    snapshot1 = create_snapshot_with_hierarchy_before_modification()
    snapshot2 = create_snapshot_with_hierarchy_after_modification()
    created_pathnames, _, _ = snapshot2.detect_modifications_from(snapshot1)
    folder_position = created_pathnames.index('folder2/')
    file_position = created_pathnames.index('folder2/file.txt')
    assert_less(folder_position, file_position)


def test_pathnames_are_deleted_before_their_parents():
    snapshot1 = create_snapshot_with_hierarchy_before_modification()
    snapshot2 = create_snapshot_with_hierarchy_after_modification()
    snapshot1.pathnames.reverse()
    deleted_pathnames = snapshot2.detect_deletions_from(snapshot1)
    folder_position = deleted_pathnames.index('folder5/')
    file_position = deleted_pathnames.index('folder5/file.txt')
    assert_greater(folder_position, file_position)


def test_etag_is_recomputed_only_if_necessary():
    snapshot1 = create_snapshot_with_etags_before_modification()
    warebox_mock = EtagRecomputingWareboxMock()
    snapshot2 = create_snapshot_with_etags_after_modification(warebox_mock)
    snapshot2.update_etag(snapshot1)
    assert_equal(snapshot2.metadata['file1.txt']['etag'], 'RECOMPUTED')
    assert_equal(snapshot2.metadata['file2.txt']['etag'], 'LAST_ETAG_02')
    assert_equal(warebox_mock.recomputed_pathnames, ['file1.txt'])


''' Helper functions: '''

def create_snapshot_with_different_filesizes():
    metadata = {}
    metadata['file1.txt'] = { 'size': 1 }
    metadata['file2.txt'] = { 'size': 9 }
    metadata['file3.txt'] = { 'size': 10 }
    metadata['file4.txt'] = { 'size': 11 }
    metadata['file5.txt'] = { 'size': 99 }
    metadata['file6.txt'] = { 'size': 100 }
    metadata['file7.txt'] = { 'size': 101 }
    metadata['file8.txt'] = { 'size': 999 }
    metadata['file9.txt'] = { 'size': 1000 }
    metadata['fileA.txt'] = { 'size': 1001 }
    metadata['fileA.txt'] = { 'size': 9999 }
    metadata['dir1/'] = { 'size': 0 }
    metadata['dir1/file1.txt'] = { 'size': 1 }
    metadata['dir1/file1.txt'] = { 'size': 5 }
    metadata['dir1/file1.txt'] = { 'size': 9 }
    metadata['dir1/dir2/'] = { 'size': 0 }
    metadata['dir1/dir2/file1.txt'] = { 'size': 10 }
    metadata['dir1/dir2/file2.txt'] = { 'size': 50 }
    metadata['dir1/dir2/file3.txt'] = { 'size': 99 }
    metadata['dir1/dir2/dir3/'] = { 'size': 0 }
    metadata['dir1/dir2/dir3/file1.txt'] = { 'size': 100 }
    metadata['dir1/dir2/dir3/file2.txt'] = { 'size': 500 }
    metadata['dir1/dir2/dir3/file3.txt'] = { 'size': 999 }
    for pathname in metadata:
        metadata[pathname]['lmtime'] = 0
        metadata[pathname]['etag'] = ''
    pathnames = metadata.keys()
    random.shuffle(pathnames)
    snapshot = WareboxSnapshot(pathnames, metadata, None)
    return snapshot

def create_snapshot_before_modification():
    metadata = {}
    metadata['file1.txt'] = { 'size': 1, 'lmtime': 0, 'etag': 'ETAG01' }
    metadata['file2.txt'] = { 'size': 1, 'lmtime': 0, 'etag': 'ETAG02' }
    metadata['file3.txt'] = { 'size': 1, 'lmtime': 0, 'etag': 'ETAG03' }
    metadata['file4.txt'] = { 'size': 1, 'lmtime': 0, 'etag': 'ETAG0B' }
    metadata['file5.txt'] = { 'size': 1, 'lmtime': 0, 'etag': 'ETAG04' }
    metadata['file6.txt'] = { 'size': 1, 'lmtime': 0, 'etag': 'ETAG05' }
    metadata['file7.txt'] = { 'size': 1, 'lmtime': 0, 'etag': 'ETAG06' }
    metadata['fileC.txt'] = { 'size': 1, 'lmtime': 0, 'etag': 'ETAG06' }
    pathnames = sorted(metadata.keys())
    snapshot = WareboxSnapshot(pathnames, metadata, None)
    snapshot._dont_copy_below_size = 1
    return snapshot

def create_snapshot_after_modification():
    metadata = {}
    metadata['file0.txt'] = { 'size': 1, 'lmtime': 0, 'etag': 'ETAG00' } # new
    metadata['file1.txt'] = { 'size': 1, 'lmtime': 0, 'etag': 'ETAG01' } # unchanged
    metadata['file2.txt'] = { 'size': 1, 'lmtime': 0, 'etag': 'ETAG12' } # modified (etag)
    metadata['file3.txt'] = { 'size': 3, 'lmtime': 0, 'etag': 'ETAG13' } # modified (etag+size)
    metadata['file4.txt'] = { 'size': 2, 'lmtime': 0, 'etag': 'ETAG0B' } # modified (size)
    metadata['file5.txt'] = { 'size': 1, 'lmtime': 0, 'etag': 'ETAG02' } # modified but copyable from "before"
    # file6.txt deleted
    metadata['file7.txt'] = { 'size': 1, 'lmtime': 0, 'etag': 'ETAG12' } # modified but copyable from "after"
    # fileC.txt deleted
    metadata['file8.txt'] = { 'size': 1, 'lmtime': 0, 'etag': 'ETAG01' } # new but copyable from "before"
    metadata['file9.txt'] = { 'size': 1, 'lmtime': 0, 'etag': 'ETAG06' } # renamed
    metadata['fileA.txt'] = { 'size': 1, 'lmtime': 0, 'etag': 'ETAG12' } # new but copyable from "after"
    metadata['fileB.txt'] = { 'size': 1, 'lmtime': 0, 'etag': 'ETAG00' } # new but copyable from "after"
    pathnames = sorted(metadata.keys())
    snapshot = WareboxSnapshot(pathnames, metadata, None)
    snapshot._dont_copy_below_size = 1
    return snapshot


def create_snapshot_with_hierarchy_before_modification():
    metadata = {}
    metadata['folder1/']          = { 'size': 0, 'lmtime': 0, 'etag': 'ETAG00' }
    metadata['folder1/file.txt']  = { 'size': 2, 'lmtime': 0, 'etag': 'ETAG01' }
    metadata['folder5/']          = { 'size': 0, 'lmtime': 0, 'etag': 'ETAG00' }
    metadata['folder5/file.txt']  = { 'size': 1, 'lmtime': 0, 'etag': 'ETAG05' }
    pathnames = sorted(metadata.keys())
    snapshot = WareboxSnapshot(pathnames, metadata, None)
    snapshot._dont_copy_below_size = 1
    return snapshot


def create_snapshot_with_hierarchy_after_modification():
    metadata = {}
    metadata['folder1/']          = {'size': 0, 'lmtime': 0, 'etag': 'ETAG00'}  # normal
    metadata['folder1/file.txt']  = {'size': 1, 'lmtime': 0, 'etag': 'ETAG01'}  # normal
    metadata['folder2/']          = {'size': 0, 'lmtime': 0, 'etag': 'ETAG00'}  # new
    metadata['folder2/file.txt']  = {'size': 3, 'lmtime': 0, 'etag': 'ETAG02'}  # new
    metadata['folder3/']          = {'size': 0, 'lmtime': 0, 'etag': 'ETAG00'}  # copied from last
    metadata['folder3/file.txt']  = {'size': 2, 'lmtime': 0, 'etag': 'ETAG01'}  # copied from last
    metadata['folder4/']          = {'size': 0, 'lmtime': 0, 'etag': 'ETAG00'}  # copied from curr
    metadata['folder4/file.txt']  = {'size': 3, 'lmtime': 0, 'etag': 'ETAG02'}  # copied from curr
    # folder5/ deleted
    # folder5/file.txt deleted
    pathnames = sorted(metadata.keys())
    snapshot = WareboxSnapshot(pathnames, metadata, None)
    snapshot._dont_copy_below_size = 1
    return snapshot


class EtagRecomputingWareboxMock(object):

    def __init__(self):
        self.recomputed_pathnames = []

    def compute_md5_hex(self, pathname):
        self.recomputed_pathnames.append(pathname)
        return 'RECOMPUTED'


def create_snapshot_with_etags_before_modification():
    metadata = {}
    metadata['file1.txt'] = {'size': 1, 'lmtime': 1, 'etag': 'LAST_ETAG_01'}
    metadata['file2.txt'] = {'size': 2, 'lmtime': 1, 'etag': 'LAST_ETAG_02'}
    pathnames = sorted(metadata.keys())
    snapshot = WareboxSnapshot(pathnames, metadata, None)
    snapshot._dont_copy_below_size = 1
    return snapshot

def create_snapshot_with_etags_after_modification(warebox_mock):
    metadata = {}
    metadata['file1.txt'] = {'size': 1, 'lmtime': 2, 'etag': 'WRONG_ETAG_01'}
    metadata['file2.txt'] = {'size': 2, 'lmtime': 1, 'etag': 'WRONG_ETAG_02'}
    pathnames = sorted(metadata.keys())
    snapshot = WareboxSnapshot(pathnames, metadata, warebox_mock)
    snapshot._dont_copy_below_size = 1
    return snapshot

