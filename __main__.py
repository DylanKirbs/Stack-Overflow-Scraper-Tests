"""
Test script for CS343 api scraper.
Simply run `python3 tests` from the root directory to run the tests.

Notes:
- To avoid over use of the stack exchange api the responses will be cached.
- This script will set the `STACKOVERFLOW_API_PORT` environment variable.

Usage:
    tests [options] [<test_id> ...]

Options:
    -h --help       Show this screen
    --port=<port>   The port to use for the api [default: 5000]

Examples:
    tests 1
"""

import atexit
import json
import logging
import os
from datetime import datetime
from time import sleep

import requests
from deepdiff import DeepDiff
from docopt import docopt
from dotenv import load_dotenv
from termcolor import colored

args = docopt(str(__doc__))
load_dotenv()

# GLOBAL IGNORE KEYS/FIELDS

GLOBAL_POPS = [
    # Keys
    'quota_max',
    'quota_remaining',
    'content_license',
    'accept_rate',
    'other_site',

    # Values
    'azure-ad-role',
    'azure-object-anchors'
]

GLOBAL_IGNORE_DIFF_CONTAINING = [
    # 'email-protection'
]


# Paths
BASE_PATH = os.path.abspath(__file__).replace("__main__.py", "")
API_DIR = os.path.join(BASE_PATH, "api_cache")
LOG_DIR = os.path.join(BASE_PATH, "logs")
RESULTS_DIR = os.path.join(os.getcwd(), "results")
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
os.makedirs(API_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)


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

        self.file_path = f"{API_DIR}/{self.meta['url'].replace("/", "_")}.json"

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
            logger.warning(f"Erroneous response from {self.meta['url']}: {response.status_code}. No changes will be made to the cache.")
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


def dynamic_pop(data: dict, pops: list[str]):
    """
    Recursively remove keys and values from a dictionary or list.

    Example:
    >>> data = {
        'key1': 'value1',
        'key2': 'value2',
        'key3': {
            'key4': 'value4',
            'key5': 'value5'
        },
        'key6': [
            'value6',
        ]
    }
    >>> pops = ['key1', 'value4', 'value6']

    >>> dynamic_pop(data, pops)
    >>> print(data)
    >>> {
        'key2': 'value2',
        'key3': {
            'key5': 'value5'
        },
        'key6': []
    }

    :param data: The data to remove items from
    :param pops: The keys or values to remove
    :return: The data with the items removed
    """

    def remove_items(d, pops):
        if isinstance(d, dict):
            keys_to_remove = [key for key in d if key in pops]
            for key in keys_to_remove:
                d.pop(key)
            for key, value in d.items():
                remove_items(value, pops)
        elif isinstance(d, list):
            items_to_remove = [item for item in d if item in pops]
            for item in items_to_remove:
                d.remove(item)
            for item in d:
                remove_items(item, pops)

    remove_items(data, pops)


def remove_from_diff(diff: dict, pops: list[str]):
    """
    Remove specific keys from the diff if one of the values contains a string in the pops list.
    If the value is an empty dict or list, it will be removed.

    Example:
    >>> diff = {
        "values_changed": {
            "root['items'][0]['external_links'][1]['link']": {
                "new_value": "/cdn-cgi/l/email-protection#43223430202c2f2f2620372a352603222e22392c2d6d202c2e",
                "old_value": "mailto:awscollective@amazon.com"
            }
        }
    >>> pops = ['email-protection']
    >>> remove_from_diff(diff, pops)
    >>> print(diff)
    >>> {}


    :param diff: The diff to remove items from
    :param pops: The strings to check for in the diff
    """

    to_pop = []
    if 'values_changed' in diff:
        for key in diff['values_changed']:
            for old_new in diff['values_changed'][key].values():
                for check in pops:
                    if (isinstance(old_new, str)) and check in old_new:
                        to_pop.append(key)
                        break

    for key in to_pop:
        diff['values_changed'].pop(key)

    # if any values are empty dicts or lists, remove them
    to_pop = []
    for key in diff.keys():
        if diff[key] == {}:
            to_pop.append(key)
        elif isinstance(diff[key], list):
            if len(diff[key]) == 0:
                to_pop.append(key)

    for key in to_pop:
        diff.pop(key)


def validate_order(t1, t2, comparison_keys):
    """
    Check if the order of the items in two dictionaries are the same.

    :param t1: The first dictionary
    :param t2: The second dictionary
    :param comparison_keys: The keys to compare the order of
    """

    mismatches = []

    for key in comparison_keys:
        if key not in t1 or key not in t2:
            continue

        if len(t1[key]) != len(t2[key]):
            mismatches.append(f"root['{key}'] : 'length mismatch'")
            continue

        for i in range(len(t1[key])):
            diff = DeepDiff(t1[key][i], t2[key][i], ignore_order=True)
            remove_from_diff(diff,  GLOBAL_IGNORE_DIFF_CONTAINING)

            if diff != {}:
                mismatches.append(f"root['{key}'][{i}] : 'items mismatch'")

    return None if len(mismatches) == 0 else mismatches


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

    # Get the response from the scraper
    logger.info(f"Test {id} [RUNNING] : Getting Scraper response")
    response = requests.get(f"{SCRAPER_URL}{endpoint}?{'&'.join(queries)}")

    # Compare the responses
    if response.status_code != 200:
        logger.error(
            f"Test {id} [FAIL] - Bad response code: {response.status_code} : {response.text}")

        out = {
            'endpoint': endpoint,
            'queries': queries,
            'response': response.json(),
        }
        with open(f'{RESULTS_DIR}/{str(id).zfill(2)}-[ERROR].json', 'w') as f:
            print(json.dumps(out, indent=4), file=f)
        return

    scraper_response = response.json()

    # Pop impossible
    dynamic_pop(cached_response, GLOBAL_POPS)
    dynamic_pop(scraper_response, GLOBAL_POPS)

    diff = DeepDiff(
        cached_response,
        scraper_response,
        ignore_order=True,
        significant_digits=2,
        truncate_datetime='minute'
    ).to_json()
    diff = json.loads(diff)

    remove_from_diff(diff, GLOBAL_IGNORE_DIFF_CONTAINING)

    if diff == {}:
        logger.debug('No differences found, checking order')
        # If the responses are the same, check the order of the items
        mismatches = validate_order(
            cached_response, scraper_response, ['items'])
        if mismatches is not None:
            diff['order_changed'] = mismatches

    out = {
        'endpoint': endpoint,
        'queries': queries,
        'diff': diff,
        'cached': cached_response,
        'scraper': scraper_response,
    }

    pass_fail = "[PASS]" if diff == {} else "[FAIL]"

    with open(f'{RESULTS_DIR}/{str(id).zfill(2)}-{pass_fail}.json', 'w') as f:
        print(json.dumps(out, indent=4), file=f)

    logger.info(f"Test {id} {pass_fail}")


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
    os.system(f"python3 stackoverflow_scraper.py > {LOG_FILE_TEMPLATE.format(service='scraper')} 2>&1 &")

    # Wait for the service to start
    logger.info("Waiting for the service to start")
    retries = 0
    while True:
        if retries > 10:
            logger.error("Failed to start the service")
            return

        retries += 1
        try:
            response = requests.get(f"{SCRAPER_URL}/this-url-should-not-exist")
        except requests.exceptions.RequestException:
            sleep(0.5)
            pass

    # Load the test cases
    with open(TEST_CASES_PATH, "r") as f:
        test_cases = json.loads(f.read())

    # Rename old results, overwrite the previous old results
    for file in os.listdir(RESULTS_DIR):
        if file.endswith(".json") and not file.startswith("old_"):
            os.rename(os.path.join(RESULTS_DIR, file),
                      os.path.join(RESULTS_DIR, f"old_{file}"))

    # Run the tests
    for idx, test in enumerate(test_cases):
        if args['<test_id>'] and str(idx+1) not in args['<test_id>']:
            continue
        run_test(idx+1, test)


if __name__ == "__main__":
    setup_logger()
    main()
