# Test script for the Stack Overflow Scraper

For the love of all things decent, please read the usage guide provided by the script. Don't try any funny buisness, just run `python3 tests` from the base directory of the the scraper. Make sure that the tests are in a subdirectory of the project directory and that it is gitignored from your project repository.

> The script caches results from the Stack Overflow API to avoid hitting the rate limit. But your webscraper is not cached, so be wary of the rate limits.

## Contributing

If you would like to contribute test cases, please add them to the `test_cases.json` file in the format:
```json
{
    // Endpoint (preceded by a forward slash) ? Query string
    "/collectives?key=value&another_key=another_value"
}
```