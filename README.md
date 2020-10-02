# tap-shipstation

This is a [Singer](https://singer.io) tap that produces JSON-formatted data
following the [Singer
spec](https://github.com/singer-io/getting-started/blob/master/docs/SPEC.md).

This tap:

- Pulls raw data from ShipStation's API (https://www.shipstation.com/developer-api/)
- Extracts the following resources:
  - [Orders](https://www.shipstation.com/developer-api/#/reference/model-order)
  - [Shipments](https://www.shipstation.com/developer-api/#/reference/shipments/list-shipments/list-shipments-w/o-parameters)
- Outputs the schema for each resource
- Incrementally pulls data based on the input state

### Getting started

Create a config JSON file with the following format. The `default_start_datetime` should be in Pacific Time (required by the ShipStation API, see [here](https://www.shipstation.com/developer-api/#/introduction/shipstation-api-requirements/datetime-format-and-time-zone)).

```
{
  "api_key": "Your ShipStation API Key",
  "api_secret": "Your ShipStation API Secret",
  "default_start_datetime": "2018-11-01 00:00:00"
}
```

You can obtain your ShipStation API key by following the instructions [here](https://help.shipstation.com/hc/en-us/articles/206638917-How-can-I-get-access-to-ShipStation-s-API-).

---

Copyright &copy; 2018 Milk Bar
