'''tzinfo timezone information for America/Porto_Acre.'''
from pytz.tzinfo import DstTzInfo
from pytz.tzinfo import memorized_datetime as d
from pytz.tzinfo import memorized_ttinfo as i

class Porto_Acre(DstTzInfo):
    '''America/Porto_Acre timezone definition. See datetime.tzinfo for details'''

    zone = 'America/Porto_Acre'

    _utc_transition_times = [
d(1,1,1,0,0,0),
d(1914,1,1,4,31,12),
d(1931,10,3,16,0,0),
d(1932,4,1,4,0,0),
d(1932,10,3,5,0,0),
d(1933,4,1,4,0,0),
d(1949,12,1,5,0,0),
d(1950,4,16,5,0,0),
d(1950,12,1,5,0,0),
d(1951,4,1,4,0,0),
d(1951,12,1,5,0,0),
d(1952,4,1,4,0,0),
d(1952,12,1,5,0,0),
d(1953,3,1,4,0,0),
d(1963,12,9,5,0,0),
d(1964,3,1,4,0,0),
d(1965,1,31,5,0,0),
d(1965,3,31,4,0,0),
d(1965,12,1,5,0,0),
d(1966,3,1,4,0,0),
d(1966,11,1,5,0,0),
d(1967,3,1,4,0,0),
d(1967,11,1,5,0,0),
d(1968,3,1,4,0,0),
d(1985,11,2,5,0,0),
d(1986,3,15,4,0,0),
d(1986,10,25,5,0,0),
d(1987,2,14,4,0,0),
d(1987,10,25,5,0,0),
d(1988,2,7,4,0,0),
        ]

    _transition_info = [
i(-16260,0,'LMT'),
i(-18000,0,'ACT'),
i(-14400,3600,'ACST'),
i(-18000,0,'ACT'),
i(-14400,3600,'ACST'),
i(-18000,0,'ACT'),
i(-14400,3600,'ACST'),
i(-18000,0,'ACT'),
i(-14400,3600,'ACST'),
i(-18000,0,'ACT'),
i(-14400,3600,'ACST'),
i(-18000,0,'ACT'),
i(-14400,3600,'ACST'),
i(-18000,0,'ACT'),
i(-14400,3600,'ACST'),
i(-18000,0,'ACT'),
i(-14400,3600,'ACST'),
i(-18000,0,'ACT'),
i(-14400,3600,'ACST'),
i(-18000,0,'ACT'),
i(-14400,3600,'ACST'),
i(-18000,0,'ACT'),
i(-14400,3600,'ACST'),
i(-18000,0,'ACT'),
i(-14400,3600,'ACST'),
i(-18000,0,'ACT'),
i(-14400,3600,'ACST'),
i(-18000,0,'ACT'),
i(-14400,3600,'ACST'),
i(-18000,0,'ACT'),
        ]

Porto_Acre = Porto_Acre()

