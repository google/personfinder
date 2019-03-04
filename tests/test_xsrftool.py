import datetime
import unittest

import config
import utils


class XsrfToolTests(unittest.TestCase):

    TEST_NOW = datetime.datetime(2010, 1, 31, 18, 0, 0)

    def setUp(self):
        utils.set_utcnow_for_test(XsrfToolTests.TEST_NOW)
        config.set(xsrf_token_key='abcdef')
        self._tool = utils.XsrfTool()

    def testGenerateAndVerifyGoodToken(self):
        token = self._tool.generate_token(12345, 'test_action')
        self.assertTrue(self._tool.verify_token(token, 12345, 'test_action'))

    def testRejectsInvalidToken(self):
        timestamp = utils.get_timestamp(XsrfToolTests.TEST_NOW)
        self.assertFalse(self._tool.verify_token(
            'NotTheRightDigest/%f' % timestamp, 12345, 'test_action'))

    def testRejectsExpiredToken(self):
        token = self._tool.generate_token(12345, 'test_action')
        utils.set_utcnow_for_test(datetime.datetime(2010, 1, 31, 22, 1, 0))
        self.assertFalse(self._tool.verify_token(token, 12345, 'test_action'))
