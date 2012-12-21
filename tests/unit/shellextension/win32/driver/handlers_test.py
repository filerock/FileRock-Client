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

import sys
if not sys.platform.startswith("win"):
    print "SKIPPED %s since Windows is needed" % __name__
else:

    from nose.tools import assert_equal, assert_true, assert_false

    from filerockclient.interfaces import PStatuses
    from filerockclient.ui.shellextension.win32.driver.shellext_pb2 import Status
    from filerockclient.ui.shellextension.win32.driver.handlers import is_encrypted, transcode_status


    def test_detects_encrypted_files_by_prefix():
        assert_true(is_encrypted(u'encrypted/'))
        assert_true(is_encrypted(u'encrypted/bar.txt'))

        assert_false(is_encrypted(u'foo/'))
        assert_false(is_encrypted(u'foo/bar.txt'))


    def test_transcodes_aligned_status():
        assert_equal(transcode_status(PStatuses.ALIGNED, False), Status.OK_CLEARTEXT)
        assert_equal(transcode_status(PStatuses.ALIGNED, True), Status.OK_ENCRYPTED)


    def test_transcodes_brokenproof_status():
        assert_equal(transcode_status(PStatuses.BROKENPROOF, False),
            Status.INTEGRITY_KO)
        assert_equal(transcode_status(PStatuses.BROKENPROOF, True),
            Status.INTEGRITY_KO)


    def test_transcodes_unknown_status():
        assert_equal(transcode_status(PStatuses.UNKNOWN, False), Status.STILL_UNSEEN)
        assert_equal(transcode_status(PStatuses.UNKNOWN, True), Status.STILL_UNSEEN)


    def test_transcodes_syncronizing_statuses():
        for pstatus in (PStatuses.TOBEUPLOADED, PStatuses.UPLOADING, PStatuses.UPLOADED,
                        PStatuses.TOBEDOWNLOADED, PStatuses.DOWNLOADING,
                        PStatuses.RENAMETOBESENT, PStatuses.RENAMESENT,
                        PStatuses.DELETETOBESENT, PStatuses.DELETESENT):
            assert_equal(transcode_status(pstatus, False), Status.SYNCRONIZING)
            assert_equal(transcode_status(pstatus, True), Status.SYNCRONIZING)
