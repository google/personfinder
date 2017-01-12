# -*- coding: ascii -*-

import sys, os, os.path
import unittest, doctest
import cPickle as pickle
from datetime import datetime, tzinfo, timedelta

if __name__ == '__main__':
    # Only munge path if invoked as a script. Testrunners should have setup
    # the paths already
    sys.path.insert(0, os.path.abspath(os.path.join(os.pardir, os.pardir)))

import pytz
from pytz import reference

EXPECTED_VERSION='2006p'

fmt = '%Y-%m-%d %H:%M:%S %Z%z'

NOTIME = timedelta(0)

# GMT is a tzinfo.StaticTzInfo--the class we primarily want to test--while
# UTC is reference implementation.  They both have the same timezone meaning.
UTC = pytz.timezone('UTC')
GMT = pytz.timezone('GMT')

class BasicTest(unittest.TestCase):

    def testVersion(self):
        # Ensuring the correct version of pytz has been loaded
        self.failUnlessEqual(EXPECTED_VERSION, pytz.__version__,
                'Incorrect pytz version loaded. Import path is stuffed '
                'or this test needs updating. (Wanted %s, got %s)'
                % (EXPECTED_VERSION, pytz.__version__)
                )

    def testGMT(self):
        now = datetime.now(tz=GMT)
        self.failUnless(now.utcoffset() == NOTIME)
        self.failUnless(now.dst() == NOTIME)
        self.failUnless(now.timetuple() == now.utctimetuple())
        self.failUnless(now==now.replace(tzinfo=UTC))

    def testReferenceUTC(self):
        now = datetime.now(tz=UTC)
        self.failUnless(now.utcoffset() == NOTIME)
        self.failUnless(now.dst() == NOTIME)
        self.failUnless(now.timetuple() == now.utctimetuple())


class PicklingTest(unittest.TestCase):

    def _roundtrip_tzinfo(self, tz):
        p = pickle.dumps(tz)
        unpickled_tz = pickle.loads(p)
        self.failUnless(tz is unpickled_tz, '%s did not roundtrip' % tz.zone)

    def _roundtrip_datetime(self, dt):
        # Ensure that the tzinfo attached to a datetime instance
        # is identical to the one returned. This is important for
        # DST timezones, as some state is stored in the tzinfo.
        tz = dt.tzinfo
        p = pickle.dumps(dt)
        unpickled_dt = pickle.loads(p)
        unpickled_tz = unpickled_dt.tzinfo
        self.failUnless(tz is unpickled_tz, '%s did not roundtrip' % tz.zone)

    def testDst(self):
        tz = pytz.timezone('Europe/Amsterdam')
        dt = datetime(2004, 2, 1, 0, 0, 0)

        for localized_tz in tz._tzinfos.values():
            self._roundtrip_tzinfo(localized_tz)
            self._roundtrip_datetime(dt.replace(tzinfo=localized_tz))

    def testRoundtrip(self):
        dt = datetime(2004, 2, 1, 0, 0, 0)
        for zone in pytz.all_timezones:
            tz = pytz.timezone(zone)
            self._roundtrip_tzinfo(tz)

    def testDatabaseFixes(self):
        # Hack the pickle to make it refer to a timezone abbreviation
        # that does not match anything. The unpickler should be able
        # to repair this case
        tz = pytz.timezone('Australia/Melbourne')
        p = pickle.dumps(tz)
        tzname = tz._tzname
        hacked_p = p.replace(tzname, '???')
        self.failIfEqual(p, hacked_p)
        unpickled_tz = pickle.loads(hacked_p)
        self.failUnless(tz is unpickled_tz)

        # Simulate a database correction. In this case, the incorrect
        # data will continue to be used.
        p = pickle.dumps(tz)
        new_utcoffset = tz._utcoffset.seconds + 42
        hacked_p = p.replace(str(tz._utcoffset.seconds), str(new_utcoffset))
        self.failIfEqual(p, hacked_p)
        unpickled_tz = pickle.loads(hacked_p)
        self.failUnlessEqual(unpickled_tz._utcoffset.seconds, new_utcoffset)
        self.failUnless(tz is not unpickled_tz)


class USEasternDSTStartTestCase(unittest.TestCase):
    tzinfo = pytz.timezone('US/Eastern')

    # 24 hours before DST changeover
    transition_time = datetime(2002, 4, 7, 7, 0, 0, tzinfo=UTC)

    # Increase for 'flexible' DST transitions due to 1 minute granularity
    # of Python's datetime library
    instant = timedelta(seconds=1)

    # before transition
    before = {
        'tzname': 'EST',
        'utcoffset': timedelta(hours = -5),
        'dst': timedelta(hours = 0),
        }

    # after transition
    after = {
        'tzname': 'EDT',
        'utcoffset': timedelta(hours = -4),
        'dst': timedelta(hours = 1),
        }

    def _test_tzname(self, utc_dt, wanted):
        tzname = wanted['tzname']
        dt = utc_dt.astimezone(self.tzinfo)
        self.failUnlessEqual(dt.tzname(), tzname,
            'Expected %s as tzname for %s. Got %s' % (
                tzname, str(utc_dt), dt.tzname()
                )
            )

    def _test_utcoffset(self, utc_dt, wanted):
        utcoffset = wanted['utcoffset']
        dt = utc_dt.astimezone(self.tzinfo)
        self.failUnlessEqual(
                dt.utcoffset(), wanted['utcoffset'],
                'Expected %s as utcoffset for %s. Got %s' % (
                    utcoffset, utc_dt, dt.utcoffset()
                    )
                )

    def _test_dst(self, utc_dt, wanted):
        dst = wanted['dst']
        dt = utc_dt.astimezone(self.tzinfo)
        self.failUnlessEqual(dt.dst(),dst,
            'Expected %s as dst for %s. Got %s' % (
                dst, utc_dt, dt.dst()
                )
            )

    def test_arithmetic(self):
        utc_dt = self.transition_time

        for days in range(-420, 720, 20):
            delta = timedelta(days=days)

            # Make sure we can get back where we started
            dt = utc_dt.astimezone(self.tzinfo)
            dt2 = dt + delta
            dt2 = dt2 - delta
            self.failUnlessEqual(dt, dt2)

            # Make sure arithmetic crossing DST boundaries ends
            # up in the correct timezone after normalization
            self.failUnlessEqual(
                    (utc_dt + delta).astimezone(self.tzinfo).strftime(fmt),
                    self.tzinfo.normalize(dt + delta).strftime(fmt),
                    'Incorrect result for delta==%d days.  Wanted %r. Got %r'%(
                        days,
                        (utc_dt + delta).astimezone(self.tzinfo).strftime(fmt),
                        self.tzinfo.normalize(dt + delta).strftime(fmt),
                        )
                    )

    def _test_all(self, utc_dt, wanted):
        self._test_utcoffset(utc_dt, wanted)
        self._test_tzname(utc_dt, wanted)
        self._test_dst(utc_dt, wanted)

    def testDayBefore(self):
        self._test_all(
                self.transition_time - timedelta(days=1), self.before
                )

    def testTwoHoursBefore(self):
        self._test_all(
                self.transition_time - timedelta(hours=2), self.before
                )

    def testHourBefore(self):
        self._test_all(
                self.transition_time - timedelta(hours=1), self.before
                )

    def testInstantBefore(self):
        self._test_all(
                self.transition_time - self.instant, self.before
                )

    def testTransition(self):
        self._test_all(
                self.transition_time, self.after
                )

    def testInstantAfter(self):
        self._test_all(
                self.transition_time + self.instant, self.after
                )

    def testHourAfter(self):
        self._test_all(
                self.transition_time + timedelta(hours=1), self.after
                )

    def testTwoHoursAfter(self):
        self._test_all(
                self.transition_time + timedelta(hours=1), self.after
                )

    def testDayAfter(self):
        self._test_all(
                self.transition_time + timedelta(days=1), self.after
                )


class USEasternDSTEndTestCase(USEasternDSTStartTestCase):
    tzinfo = pytz.timezone('US/Eastern')
    transition_time = datetime(2002, 10, 27, 6, 0, 0, tzinfo=UTC)
    before = {
        'tzname': 'EDT',
        'utcoffset': timedelta(hours = -4),
        'dst': timedelta(hours = 1),
        }
    after = {
        'tzname': 'EST',
        'utcoffset': timedelta(hours = -5),
        'dst': timedelta(hours = 0),
        }


class USEasternEPTStartTestCase(USEasternDSTStartTestCase):
    transition_time = datetime(1945, 8, 14, 23, 0, 0, tzinfo=UTC)
    before = {
        'tzname': 'EWT',
        'utcoffset': timedelta(hours = -4),
        'dst': timedelta(hours = 1),
        }
    after = {
        'tzname': 'EPT',
        'utcoffset': timedelta(hours = -4),
        'dst': timedelta(hours = 1),
        }


class USEasternEPTEndTestCase(USEasternDSTStartTestCase):
    transition_time = datetime(1945, 9, 30, 6, 0, 0, tzinfo=UTC)
    before = {
        'tzname': 'EPT',
        'utcoffset': timedelta(hours = -4),
        'dst': timedelta(hours = 1),
        }
    after = {
        'tzname': 'EST',
        'utcoffset': timedelta(hours = -5),
        'dst': timedelta(hours = 0),
        }


class WarsawWMTEndTestCase(USEasternDSTStartTestCase):
    # In 1915, Warsaw changed from Warsaw to Central European time.
    # This involved the clocks being set backwards, causing a end-of-DST
    # like situation without DST being involved.
    tzinfo = pytz.timezone('Europe/Warsaw')
    transition_time = datetime(1915, 8, 4, 22, 36, 0, tzinfo=UTC)
    before = {
        'tzname': 'WMT',
        'utcoffset': timedelta(hours=1, minutes=24),
        'dst': timedelta(0),
        }
    after = {
        'tzname': 'CET',
        'utcoffset': timedelta(hours=1),
        'dst': timedelta(0),
        }


class VilniusWMTEndTestCase(USEasternDSTStartTestCase):
    # At the end of 1916, Vilnius changed timezones putting its clock
    # forward by 11 minutes 35 seconds. Neither timezone was in DST mode.
    tzinfo = pytz.timezone('Europe/Vilnius')
    instant = timedelta(seconds=31)
    transition_time = datetime(1916, 12, 31, 22, 36, 00, tzinfo=UTC)
    before = {
        'tzname': 'WMT',
        'utcoffset': timedelta(hours=1, minutes=24),
        'dst': timedelta(0),
        }
    after = {
        'tzname': 'KMT',
        'utcoffset': timedelta(hours=1, minutes=36), # Really 1:35:36
        'dst': timedelta(0),
        }


class ReferenceUSEasternDSTStartTestCase(USEasternDSTStartTestCase):
    tzinfo = reference.Eastern
    def test_arithmetic(self):
        # Reference implementation cannot handle this
        pass


class ReferenceUSEasternDSTEndTestCase(USEasternDSTEndTestCase):
    tzinfo = reference.Eastern

    def testHourBefore(self):
        # Python's datetime library has a bug, where the hour before
        # a daylight savings transition is one hour out. For example,
        # at the end of US/Eastern daylight savings time, 01:00 EST
        # occurs twice (once at 05:00 UTC and once at 06:00 UTC),
        # whereas the first should actually be 01:00 EDT.
        # Note that this bug is by design - by accepting this ambiguity
        # for one hour one hour per year, an is_dst flag on datetime.time
        # became unnecessary.
        self._test_all(
                self.transition_time - timedelta(hours=1), self.after
                )

    def testInstantBefore(self):
        self._test_all(
                self.transition_time - timedelta(seconds=1), self.after
                )

    def test_arithmetic(self):
        # Reference implementation cannot handle this
        pass


class LocalTestCase(unittest.TestCase):
    def testLocalize(self):
        loc_tz = pytz.timezone('Europe/Amsterdam')

        loc_time = loc_tz.localize(datetime(1930, 5, 10, 0, 0, 0))
        # Actually +00:19:32, but Python datetime rounds this
        self.failUnlessEqual(loc_time.strftime('%Z%z'), 'AMT+0020')

        loc_time = loc_tz.localize(datetime(1930, 5, 20, 0, 0, 0))
        # Actually +00:19:32, but Python datetime rounds this
        self.failUnlessEqual(loc_time.strftime('%Z%z'), 'NST+0120')

        loc_time = loc_tz.localize(datetime(1940, 5, 10, 0, 0, 0))
        self.failUnlessEqual(loc_time.strftime('%Z%z'), 'NET+0020')

        loc_time = loc_tz.localize(datetime(1940, 5, 20, 0, 0, 0))
        self.failUnlessEqual(loc_time.strftime('%Z%z'), 'CEST+0200')

        loc_time = loc_tz.localize(datetime(2004, 2, 1, 0, 0, 0))
        self.failUnlessEqual(loc_time.strftime('%Z%z'), 'CET+0100')

        loc_time = loc_tz.localize(datetime(2004, 4, 1, 0, 0, 0))
        self.failUnlessEqual(loc_time.strftime('%Z%z'), 'CEST+0200')

        tz = pytz.timezone('Europe/Amsterdam')
        loc_time = loc_tz.localize(datetime(1943, 3, 29, 1, 59, 59))
        self.failUnlessEqual(loc_time.strftime('%Z%z'), 'CET+0100')


        # Switch to US
        loc_tz = pytz.timezone('US/Eastern')

        # End of DST ambiguity check
        loc_time = loc_tz.localize(datetime(1918, 10, 27, 1, 59, 59), is_dst=1)
        self.failUnlessEqual(loc_time.strftime('%Z%z'), 'EDT-0400')

        loc_time = loc_tz.localize(datetime(1918, 10, 27, 1, 59, 59), is_dst=0)
        self.failUnlessEqual(loc_time.strftime('%Z%z'), 'EST-0500')

        self.failUnlessRaises(pytz.AmbiguousTimeError,
                loc_tz.localize, datetime(1918, 10, 27, 1, 59, 59), is_dst=None
                )

        # Weird changes - war time and peace time both is_dst==True

        loc_time = loc_tz.localize(datetime(1942, 2, 9, 3, 0, 0))
        self.failUnlessEqual(loc_time.strftime('%Z%z'), 'EWT-0400')

        loc_time = loc_tz.localize(datetime(1945, 8, 14, 19, 0, 0))
        self.failUnlessEqual(loc_time.strftime('%Z%z'), 'EPT-0400')

        loc_time = loc_tz.localize(datetime(1945, 9, 30, 1, 0, 0), is_dst=1)
        self.failUnlessEqual(loc_time.strftime('%Z%z'), 'EPT-0400')

        loc_time = loc_tz.localize(datetime(1945, 9, 30, 1, 0, 0), is_dst=0)
        self.failUnlessEqual(loc_time.strftime('%Z%z'), 'EST-0500')

    def testNormalize(self):
        tz = pytz.timezone('US/Eastern')
        dt = datetime(2004, 4, 4, 7, 0, 0, tzinfo=UTC).astimezone(tz)
        dt2 = dt - timedelta(minutes=10)
        self.failUnlessEqual(
                dt2.strftime('%Y-%m-%d %H:%M:%S %Z%z'),
                '2004-04-04 02:50:00 EDT-0400'
                )

        dt2 = tz.normalize(dt2)
        self.failUnlessEqual(
                dt2.strftime('%Y-%m-%d %H:%M:%S %Z%z'),
                '2004-04-04 01:50:00 EST-0500'
                )

    def testPartialMinuteOffsets(self):
        # utcoffset in Amsterdam was not a whole minute until 1937
        # However, we fudge this by rounding them, as the Python
        # datetime library 
        tz = pytz.timezone('Europe/Amsterdam')
        utc_dt = datetime(1914, 1, 1, 13, 40, 28, tzinfo=UTC) # correct
        utc_dt = utc_dt.replace(second=0) # But we need to fudge it
        loc_dt = utc_dt.astimezone(tz)
        self.failUnlessEqual(
                loc_dt.strftime('%Y-%m-%d %H:%M:%S %Z%z'),
                '1914-01-01 14:00:00 AMT+0020'
                )

        # And get back...
        utc_dt = loc_dt.astimezone(UTC)
        self.failUnlessEqual(
                utc_dt.strftime('%Y-%m-%d %H:%M:%S %Z%z'),
                '1914-01-01 13:40:00 UTC+0000'
                )

    def no_testCreateLocaltime(self):
        # It would be nice if this worked, but it doesn't.
        tz = pytz.timezone('Europe/Amsterdam')
        dt = datetime(2004, 10, 31, 2, 0, 0, tzinfo=tz)
        self.failUnlessEqual(
                dt.strftime(fmt),
                '2004-10-31 02:00:00 CET+0100'
                )

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite('pytz'))
    suite.addTest(doctest.DocTestSuite('pytz.tzinfo'))
    import test_tzinfo
    suite.addTest(unittest.defaultTestLoader.loadTestsFromModule(test_tzinfo))
    return suite

DEFAULT = test_suite()

if __name__ == '__main__':
    unittest.main(defaultTest='DEFAULT')

