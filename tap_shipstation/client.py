import time
import requests
import pendulum
import singer

LOGGER = singer.get_logger()
BASE_URL = 'https://ssapi.shipstation.com/'
PAGE_SIZE = 100

def prepare_datetime(dt):
    # ShipStation requests must be in Pacific timezone
    timezone = pendulum.timezone('America/Los_Angeles')
    converted = timezone.convert(dt).strftime('%Y-%m-%d %H:%M:%S')
    return converted

class ShipStationClient:
    def __init__(self, config):
        self.username = config['api_key']
        self.password = config['api_secret']

    def make_request(self, url, params):
        LOGGER.info('Making request to %s with query parameters %s', url, params)
        params['pageSize'] = PAGE_SIZE
        response = requests.get(url, params=params, auth=(self.username, self.password))
        return response

    def paginate(self, endpoint, params):
        url = BASE_URL + endpoint        
        while True:
            response = self.make_request(url, params)
            headers = response.headers
            response_json = response.json()
            status_code = response.status_code
            if status_code == 200:
                if response_json['total'] == 0:
                    LOGGER.info('No Data for endpoint')
                    break
                yield response_json[endpoint]
                LOGGER.info(
                    'Finished requesting page %s out of %s total pages.',
                    response_json['page'],
                    response_json['pages'])
                if response_json['page'] >= response_json['pages']:
                    break
                params['page'] += 1

                # Respect API rate limits
                if int(headers['X-Rate-Limit-Remaining']) < 1:
                    wait_seconds = int(headers['X-Rate-Limit-Reset']) + 1 # Buffer of 1 second
                    LOGGER.info(
                        "Waiting for % seconds to respect ShipStation's API rate limit.",
                        wait_seconds)
                    time.sleep(wait_seconds)
            elif status_code == 429:
                time.sleep(60)
                LOGGER.info("Waiting for 60 seconds due to 429 without warning")
            else:
                response.raise_for_status()