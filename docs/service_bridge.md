# Service Bridge

The fullctl service bridge is a way for fullctl services to exchange information seamlessly using the RESTful api.

## ServiceBridgeModel

The `ServiceBridgeModel` base class allows a django model to have a main reference at another service.

This reference can then be used to populate data, either once, or continuously if the reference is flagged as the
source for truth.

### Use case(s)

- **deviceCtl** pulling in device data from **nautobot**

## ServiceBridgeAction

`ServiceBridgeAction` allows one to add database controlled additional pull or push actions for a model through django admin.

These can be used to push data from the model to its references, or pull in additional data from secondary references.

### Use case(s)

- **deviceCtl** pushing facility data and device locations to **nautobot**

### Overview of `client.py` (Service Bridge Client)

The `client.py` module within the `fullctl` package provides a robust and flexible framework for interacting with different services via HTTP, particularly focusing on facilitating communication and data exchange with service bridges.

#### Key Components:

- **Bridge Class:** Serves as the base class for creating service bridges. It handles the construction of HTTP requests, execution, and response parsing with features to support caching, authentication, and error handling. Key methods include `get`, `post`, `put`, `patch`, `delete`, for performing respective HTTP operations, and methods like `object`, `objects`, `create`, `destroy`, `update`, etc., for high-level operations on service entities.
- **ServiceBridgeError and AuthError Classes:** Custom exceptions to handle service bridge related errors and authentication errors specifically.

- **Utility Functions:** Includes `trim_endpoint` and `url_join` for manipulating URL strings to ensure correct endpoint formatting.

- **DataObject Class:** A basic structure for representing data objects retrieved through service bridges. It defines a minimal interface expected from data objects, making it extensible for specific service needs.

#### How to Use:

To use the service bridge client, one would typically extend the `Bridge` class to create a service-specific client. For example, to create a client for a hypothetical service `Xyz`, one would:
1. Define a subclass of `Bridge`, say `XyzBridge`.
2. Possibly override `url_prefix`, `results_key`, and the inner `Meta` class attributes to suit the specifics of the `Xyz` service.
3. Implement any additional methods if needed, or use the existing ones to interact with the `Xyz` service.

```python
class XyzBridge(Bridge):
    url_prefix = "data"
    results_key = "results"
    class Meta:
        service = "xyz"
        ref_tag = "xyz"
        data_object_cls = XyzDataObject
```

Then, you can use this class to perform API operations against the `Xyz` service.

### Extra Information for the Nautobot Client (`nautobot.py`):

The `nautobot.py` module extends the functionality provided by `client.py` to specially cater to interactions with the Nautobot service. It introduces specialized classes derived from both `Bridge` and `DataObject` to specifically handle the nuances of Nautobot's data models and API behaviors.

#### Key Components:

- **Nautobot(Bridge) Class:** Specially tailored for integrating with Nautobot API. It defines Nautobot-specific attributes like `url_prefix` and `results_key`, and it handles authorization headers by incorporating Nautobot-specific tokens.

- **NautobotObject(DataObject) Class:** Serves as the base class for Nautobot data models, setting a default `source` and providing a standard structure for all Nautobot objects.

- **Specific Object Classes:** Defines Nautobot-specific data object classes like `DeviceTypeObject`, `DeviceObject`, `InterfaceObject`, etc., each tailored for particular Nautobot data types.

- **Usage Example:** Just like with `client.py`, you would extend the `Nautobot` class for specific use-cases. It's pre-configured to work with Nautobot, so integration is mainly about utilizing its methods to communicate with Nautobot API endpoints, handling Nautobot objects, etc.

This setup greatly facilitates the development of services integrating with Nautobot by providing a structured and coherent way to manage Nautobot data and interact with its API, leveraging the foundational service bridge framework established by `client.py`.

### Nautobot Service Bridge Usage Example

#### Authentication
Interactions with the Nautobot service via the service bridge utilize an internal service API key for authentication. This key is typically set automatically through application environment settings, emphasizing the distinction from directly using Nautobot API tokens. This abstraction allows for flexible integration patterns.

#### Retrieving a List of Devices

To list devices managed by Nautobot:

```python
from fullctl.service_bridge.nautobot import Device

# Initialize the Nautobot Device client
# The service API key is automatically handled; no need to explicitly provide it here
device_client = Device(org='your_org_here')  # Provide the organization slug

# Retrieve and print all device names and their IDs
for device in device_client.objects():
    print(f"ID: {device.id}, Name: {device.name}")
```

#### Updating a Device with Overridden API Key

Under circumstances that require using a different internal service API key than the default one:

```python
device_id = 'your_device_id_here'
new_data = {'name': 'New Device Name'}
# Optionally, specify a different service API key
custom_api_key = 'your_custom_service_api_key_here'

try:
    # Initialize the client with a custom API key, if needed
    device_client = Device(key=custom_api_key, org='your_org_here')
    # Retrieve the device object first
    device = device_client.object(device_id)
    # Update the device
    updated_device = device_client.update(device, new_data)
    print(f"Device updated. New Name: {updated_device.name}")
except ServiceBridgeError as e:
    print(f"An error occurred: {str(e)}")
```

#### Note on API Key Management

Manage internal service API keys securely and ensure they are correctly set through your environment's configuration. The ability to override these keys allows for various scenarios like testing or interacting with multiple Nautobot instances.
