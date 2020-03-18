from pkg_resources import get_distribution, DistributionNotFound

try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    # package is not installed
    __version__ = "unknown"

__title__ = 'ledger_sim'
__author__ = 'Chia Network'
__license__ = 'Apache'
__copyright__ = 'Copyright 2019 Chia Network'
