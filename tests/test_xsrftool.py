import datetime
import unittest

import config
import utils


class XsrfToolTests(unittest.TestCase):

    TEST_NOW = datetime.datetime(2010, 1, 31, 18, 0, 0)

    def setUp(self):
        utils.set_utcnow_for_test(XsrfToolTests.TEST_NOW)

    def testGenerateAndVerifyGoodToken(self):
        config.set(xsrf_token_key='abcdef')
        tool = utils.XsrfTool()
        token = tool.generate_token(12345, 'test_action')
        self.assertTrue(tool.verify_token(token, 12345, 'test_action'))

    def testRejectsInvalidToken(self):
        config.set(xsrf_token_key='abcdef')
        tool = utils.XsrfTool()
        timestamp = utils.get_timestamp(XsrfToolTests.TEST_NOW)
        self.assertFalse(tool.verify_token(
            'NotTheRightDigest/%f' % timestamp, 12345, 'test_action'))

    def testRejectsExpiredToken(self):
        config.set(xsrf_token_key='abcdef')
        tool = utils.XsrfTool()
        token = tool.generate_token(12345, 'test_action')
        utils.set_utcnow_for_test(datetime.datetime(2010, 1, 31, 22, 1, 0))
        self.assertFalse(tool.verify_token(token, 12345, 'test_action'))

    def testGoodTokenWithNoPriorTokenKey(self):
        # config seems to be shared across tests, so we have to specifically set
        # it to None.
        config.set(xsrf_token_key=None)
        tool = utils.XsrfTool()
        token = tool.generate_token(12345, 'test_action')
        self.assertTrue(tool.verify_token(token, 12345, 'test_action'))

    def testBadTokenWithNoPriorTokenKey(self):
        # config seems to be shared across tests, so we have to specifically set
        # it to None.
        config.set(xsrf_token_key=None)
        tool = utils.XsrfTool()
        timestamp = utils.get_timestamp(XsrfToolTests.TEST_NOW)
        self.assertFalse(tool.verify_token(
            'NotTheRightDigest/%f' % timestamp, 12345, 'test_action'))
