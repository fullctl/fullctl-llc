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


