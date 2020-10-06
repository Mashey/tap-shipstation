import os
import json
import jsonref
from datetime import datetime
from datetime import timedelta
import pendulum
import singer
from singer import utils, metadata
from .client import ShipStationClient
from .client import prepare_datetime

REQUIRED_CONFIG_KEYS = ['api_key', 'api_secret', 'default_start_datetime']
LOGGER = singer.get_logger()

def get_abs_path(path):
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), path)

def load_schemas():
    schemas = {}
    for filename in os.listdir(get_abs_path('schemas')):
        path = get_abs_path('schemas') + '/' + filename
        file_raw = filename.replace('.json', '')
        with open(path) as file:
            schemas[file_raw] = jsonref.load(file)

    return schemas

def discover():
    raw_schemas = load_schemas()

    streams = []

    keys = {
        'orders' : ['orderId'],
        'shipments' : ['shipmentId']
    }

    for schema_name, schema in raw_schemas.items():
        top_level_metadata = {
            'selected': True,
            'selected-by-default': True,
            'inclusion': 'available',
            'table-key-properties': keys[schema_name]}

        metadata_entry = singer.metadata.new()
        for key, value in top_level_metadata.items():
            metadata_entry = singer.metadata.write(
                compiled_metadata=metadata_entry,
                breadcrumb=(),
                k=key,
                val=value)

        catalog_entry = {
            'stream': schema_name,
            'tap_stream_id': schema_name,
            'schema': schema,
            'key_properties': keys[schema_name],
            'metadata' : singer.metadata.to_list(metadata_entry)
        }
        streams.append(catalog_entry)

    return {'streams': streams}

def get_selected_streams(catalog):
    '''
    Gets selected streams.  Checks schema's 'selected' first (legacy)
    and then checks metadata (current), looking for an empty breadcrumb
    and mdata with a 'selected' entry
    '''
    selected_streams = []
    for stream in catalog.streams:
        stream_metadata = metadata.to_map(stream.metadata)
        # stream metadata will have an empty breadcrumb
        if metadata.get(stream_metadata, (), "selected"):
            selected_streams.append(stream.tap_stream_id)

    return selected_streams

def sync(config, state, catalog):
    selected_stream_ids = get_selected_streams(catalog)

    # Loop over streams in catalog
    for stream in catalog.streams:
        stream_id = stream.tap_stream_id
        stream_schema = stream.schema
        if stream_id in selected_stream_ids:
            LOGGER.info("Beginning sync of stream '%s'.", stream_id)
            singer.write_schema(
                stream_id,
                stream_schema.to_dict(),
                stream.key_properties)

            client = ShipStationClient(config)
            bookmark = singer.get_bookmark(
                state=state,
                tap_stream_id=stream_id,
                key='modifyDate')

            if bookmark:
                start_at = pendulum.parse(bookmark, tz='America/Los_Angeles')
            else:
                start_at = pendulum.parse(config['default_start_datetime'], tz='America/Los_Angeles')

            stream_end_at = pendulum.now('America/Los_Angeles')

            stream_date_types = {
                'orders' : ['modify'],
                'shipments' : ['create','void']
            }

            end_at = start_at
            while end_at < stream_end_at:
                #Increment queries by 1 day, limit to stream end datetime
                end_at += timedelta(days=1)
                if end_at > stream_end_at:
                    end_at = stream_end_at
                #For endpoints requiring multiple queries, cycle through timestamps
                for query_date_type in stream_date_types[stream_id]:
                    params = {
                        query_date_type + 'DateStart': prepare_datetime(start_at),
                        query_date_type + 'DateEnd': prepare_datetime(end_at),
                        'page': 1}
                    if stream_id == 'shipments':
                        params['includeShipmentItems'] = True
                        #Don't bring over voided shipments unless looking for void explicitly
                        if query_date_type != 'void':
                            params['void'] = False
                    pages = client.paginate(stream_id, params)
                    for page in pages:
                        for record in page:
                            transformed = singer.transform(record, stream_schema.to_dict())
                            singer.write_record(stream_id, transformed)

                #Write state at end of daily loop for stream
                state = singer.write_bookmark(
                    state=state,
                    tap_stream_id=stream_id,
                    key='modifyDate',
                    val=end_at.strftime("%Y-%m-%d %H:%M:%S"))
                singer.write_state(state)
                start_at = end_at              

            LOGGER.info("Finished syncing stream '%s'.", stream_id)

@utils.handle_top_exception(LOGGER)
def main():
    # Parse command line arguments
    args = utils.parse_args(REQUIRED_CONFIG_KEYS)

    # If discover flag was passed, run discovery mode and dump output to stdout
    if args.discover:
        catalog = discover()
        print(json.dumps(catalog, indent=2))
    # Otherwise run in sync mode
    else:
        if args.catalog:
            catalog = args.catalog
        else:
            catalog = discover()

        sync(args.config, args.state, catalog)

if __name__ == "__main__":
    main()
