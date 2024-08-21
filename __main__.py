"""
Test script for CS343 api scraper.
Simply run `python3 tests` from the root directory to run the tests.

Notes:
- To avoid over use of the stack exchange api the responses will be cached.
- This script will set the `STACKOVERFLOW_API_PORT` environment variable.

Usage:
    tests [options]

Options:
    -h --help       Show this screen
    --port=<port>   The port to use for the api [default: 5000]
"""

import atexit
import json
import logging
import os
from datetime import datetime

import requests
from deepdiff import DeepDiff
from docopt import docopt
from dotenv import load_dotenv
from termcolor import colored

args = docopt(str(__doc__))
load_dotenv()


# Paths
BASE_PATH = os.path.abspath(__file__).replace("__main__.py", "")
API_CACHE_DIR = os.path.join(BASE_PATH, "api_cache")
LOG_DIR = os.path.join(BASE_PATH, "logs")
TEST_CASES_PATH = os.path.join(BASE_PATH, "test_cases.json")

LOG_FILE_TEMPLATE = os.path.join(
    LOG_DIR, datetime.now().strftime('%Y%m%d-%H%M%S') + "-{service}.log")

# Port
SCRAPER_PORT = args.get(
    '--port', os.environ.get('STACKOVERFLOW_API_PORT', 5000))
os.environ.setdefault('STACKOVERFLOW_API_PORT', SCRAPER_PORT)


# URLs
SCRAPER_URL = f"http://localhost:{SCRAPER_PORT}"
API_URL = "https://api.stackexchange.com/2.3"  # must include ?site=stackoverflow


# Create the directories
os.makedirs(API_CACHE_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)


# If the test cases file does not exist, create it
if not os.path.exists(TEST_CASES_PATH):
    with open(TEST_CASES_PATH, "w") as f:
        f.write("[]")

    print("Warning, no test cases found. Please add test cases to test_cases.json")


logger = logging.getLogger()


class CustomFormatter(logging.Formatter):

    _colorRules = {
        'DEBUG': lambda s: colored(s, 'blue'),
        'INFO': lambda s: colored(s, 'green'),
        'WARNING': lambda s: colored(s, 'yellow'),
        'ERROR': lambda s: colored(s, 'red'),
        'CRITICAL': lambda s: colored(s, 'red', attrs=['bold'])
    }

    def __init__(self, format_str=None, additional_rules=None):

        if format_str:
            super().__init__(format_str)
        else:
            super().__init__()

        if additional_rules:
            self._colorRules.update(additional_rules)

    def format(self, record):
        formatted_str = super().format(record)

        for rule in self._colorRules:
            formatted_str = formatted_str.replace(
                rule, self._colorRules[rule](rule))

        return formatted_str


class API_Cache:
    """
    A class to cache the results of an API request
    """

    def __init__(self, url, update_interval=600):
        """
        Creates a new API_Cache object

        :param url: The url to cache
        :param update_interval: The time in seconds between updates (default 10 minutes)
        """
        self.meta = {
            'last_update': 0,
            'url': url,
            'update_interval': update_interval
        }
        self.cache = {}

        self.file_path = f"{
            API_CACHE_DIR}/{self.meta['url'].replace("/", "_")}.json"

        if not os.path.exists(self.file_path):
            self._save()

    def fetch(self) -> dict:
        """
        Get the contents of the cache file.
        If the cache is out of date the cache will be updated.

        Warning: If the cache is unable to be updated the old cache will be returned, this may be out of date.

        :return: The cache
        """

        self._load()

        if (datetime.now().timestamp() - self.meta['last_update']) > self.meta['update_interval']:
            self.refresh()

        return self.cache

    def refresh(self):
        """
        Query the URL and update the cache upon success.
        """

        try:
            response = requests.get(self.meta['url'])
        except requests.exceptions.RequestException as e:
            logger.warning(
                f"Request to {self.meta['url']} failed. No changes will be made to the cache.")
            logger.debug(e)
            return

        if response.status_code != 200:
            logger.warning(f"Erroneous response from {
                           self.meta['url']}: {response.status_code}. No changes will be made to the cache.")
            logger.debug(response.text)
            return

        self.cache = response.json()
        self.meta['last_update'] = datetime.now().timestamp()

        self._save()

    def _save(self):
        """
        Save the cache to the cache file
        """

        data = {
            'meta': self.meta,
            'cache': self.cache
        }

        with open(self.file_path, "w") as f:
            f.write(json.dumps(data))

    def _load(self):
        """
        Load the cache from the cache file
        """

        with open(self.file_path, "r") as f:
            data = json.loads(f.read())

        self.meta = data['meta']
        self.cache = data['cache']


def setup_logger():

    logger.setLevel(logging.INFO)
    formatter = CustomFormatter(
        "[%(asctime)s] %(levelname)s: %(message)s",
        {
            '[START]': lambda s: colored(s, 'black', 'on_blue', attrs=['bold']),
            '[PASS]': lambda s: colored(s, 'black', 'on_green', attrs=['bold']),
            '[FAIL]': lambda s: colored(s, 'black', 'on_red', attrs=['bold']),
            '[RUNNING]': lambda s: colored(s, 'black', 'on_yellow', attrs=['bold']),
        })

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # File handler
    fh = logging.FileHandler(LOG_FILE_TEMPLATE.format(service="tester"))
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)


def run_test(id: int, endpoint: str):
    """
    Make a call to the cached api and the scraper endpoints and compare the results.

    :param id: The uid of the test case
    :param endpoint: The endpoint to compare
    """

    split_endpoint = endpoint.strip().split("?")
    endpoint = split_endpoint[0]
    queries = split_endpoint[1].split("&") if len(split_endpoint) > 1 else []
    queries.append("site=stackoverflow")

    logger.info(f"Test {id} [START] : {endpoint}?{'&'.join(queries)}")

    # Get the cached response
    logger.info(f"Test {id} [RUNNING] : Getting API response")
    cached_api = API_Cache(f"{API_URL}{endpoint}?{'&'.join(queries)}")
    cached_response = cached_api.fetch()

    # Pop Quota info
    cached_response.pop('quota_max')
    cached_response.pop('quota_remaining')

    # Get the response from the scraper
    logger.info(f"Test {id} [RUNNING] : Getting Scraper response")
    response = requests.get(f"{SCRAPER_URL}{endpoint}?{'&'.join(queries)}")

    # Compare the responses
    if response.status_code != 200:
        logger.error(
            f"Test {id} [FAIL] - Bad response code: {response.status_code} : {response.text}")
        return

    scraper_response = response.json()

    diff = DeepDiff(cached_response, scraper_response, ignore_order=True)
    out = {
        'diff': diff.to_dict(),
        'cached': cached_response,
        'scraper': scraper_response,
    }
    print(json.dumps(out, indent=4), file=open(f'results/{id}.json', 'w'))
    logger.info(
        f"Test {id} [RUNNING] : Results written to results/{id}.json")

    if diff == {}:
        logger.info(f"Test {id} [PASS] : No differences found")
    else:
        logger.info(f"Test {id} [FAIL] : Differences found")


@atexit.register
def exit_service():
    """
    Runs if the script fails. This is a backup to ensure the scraper service is killed.
    """

    logger.info("Stopping the scraper service")
    os.system(f"pkill -f stackoverflow_scraper.py")


def main():

    # Start the scraper service
    logger.info(f"Starting the scraper service on port {SCRAPER_PORT}")
    os.system(f"python3 stackoverflow_scraper.py > {
              LOG_FILE_TEMPLATE.format(service='scraper')} 2>&1 &")

    # Wait for the service to start
    logger.info("Waiting for the service to start")
    while True:
        try:
            response = requests.get(f"{SCRAPER_URL}/questions")
            if response.status_code == 200:
                break
        except requests.exceptions.RequestException:
            pass

    # Load the test cases
    with open(TEST_CASES_PATH, "r") as f:
        test_cases = json.loads(f.read())

    # Do a bad endpoint test
    logger.info(f"Test 0 [START] : bad-endpoint")
    resp = requests.get(f"{SCRAPER_URL}/bad-endpoint")
    if resp.status_code != 400:
        logger.info(f"Test 0 [FAIL] : Bad endpoint did not return 400")
    else:
        logger.info(f"Test 0 [PASS] : Bad endpoint returned 400")

    # Run the tests
    for idx, test in enumerate(test_cases):
        run_test(idx+1, test)


if __name__ == "__main__":
    setup_logger()
    main()
