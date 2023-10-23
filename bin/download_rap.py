
# Downloads RAP data files for annual vegetation cover and vegetation biomass.
# Downloads multiple files concurrently to maximize transfer speed. Files that
# already exist locally will not be downloaded again.

from concurrent.futures import ThreadPoolExecutor
import subprocess as sp
import sys
from urllib.parse import urlparse
import os.path


vegcover_baseurl = 'http://rangeland.ntsg.umt.edu/data/rap/rap-vegetation-cover/v3/vegetation-cover-v3-{0}.tif'
vegcover_years = range(1986, 2023)
biomass_baseurl = 'http://rangeland.ntsg.umt.edu/data/rap/rap-vegetation-biomass/v3/vegetation-biomass-v3-{0}.tif'
biomass_years = range(1986, 2023)

# Download up to 10 files concurrently.
max_threads = 10


def download_file(url):
    fname = os.path.basename(urlparse(url).path)
    if os.path.isfile(fname):
        print(f'{fname} already downloaded, skipping...')
    else:
        print(f'Downloading {url}...')
        sp.run(['wget', '-q', url])


with ThreadPoolExecutor(max_workers=max_threads) as runner:
    for year in vegcover_years:
        url = vegcover_baseurl.format(year)
        runner.submit(download_file, url)

    for year in biomass_years:
        url = biomass_baseurl.format(year)
        runner.submit(download_file, url)

