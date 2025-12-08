## Settings

### OAuth

- `OAUTH_TWENTYC_URL` - "https://account.20c.com"
- `OAUTH_TWENTYC_KEY` - oauth application client id
- `OAUTH_TWENTYC_SECRET` - oauth application secret

### Analytics

- `GOOGLE_ANALYTICS_ID` - key for Google analytics
- `CLOUDFLARE_ANALYTICS_ID` - key for Cloudflare analytics

### Service Bridge

- `SERVICE_KEY` - api key to use for fullctl service bridge communications
- `AAACTL_URL` - host url for aaactl service (e.g., "https://account.fullctl.com"). This will automatically be defaulted to `OAUTH_TWENTYC_URL`
- `PDBCTL_URL` - host url for pdbctl service (e.g., "https://pdb.fullctl.com")
- `IXCTL_URL` - host url for ixctl service (e.g., "https://ix.fullctl.com")
- `PEERCTL_URL` - host url for peerctl service (e.g., "https://peer.fullctl.com")
- `PREFIXCTL_URL` - host url for prefixctl service (e.g., "https://prefix.fullctl.com")
- `DEVICECTL_URL` - host url for devicectl service (e.g., "https://device.fullctl.com")
- `BRIDGE_OBJECTS_CHUNK_SIZE` - Size of chunks for objects when making bridge requests

### Logging

- `AUDITCTL_LOG_API_ACTIONS` - set up logging of REST api actions to auditctl. Should be a comma separated list of ref tags or ref_tag:action pairs. For example, `ix` or `ix,member` or `ix:create,ix:delete,member:delete`.

### Operational

- `HOST_URL` - will be used when creating links back to the service in instances where the host cannot be retrieved from a http request.
- `GOOGLE_ANALYTICS_ID` - google analytics id, if set will embed analytics code

### Tasks

- `TASK_ORM_WORKER_ID` - allows you to specify a custom worker id for tasks processed in this environment, defaults to `{socket.gethostname()}:{os.getpid()}`

### PeeringDB

- `PDB_ENDPOINT` - PeeringDB host url, defaults to "https://www.peeringdb.com"
- `PDB_API_URL` - allows you to specify a custom peeringdb api location to use for the `fullctl_peeringdb_sync` command. Defaults to `{PDB_ENDPOINT}/api`.
- `PDB_API_USERNAME`
- `PDB_API_PASSWORD`

### Development and Testing

- `BILLING_INTEGRATIOON` - if False will disable all billing checks
- `SERVICE_TAG` - should be the service reference tag (e.g., 'ixctl')
- `USE_LOCAL_PERMISSIONS` - if `True` permissions will be handled locally instead of through aaactl.

### Support

- `CONTACT_US_EMAIL` - email address to send contact us messages to, defaults to `SUPPORT_EMAIL`
- `SUPPORT_EMAIL` - email address to send support messages to, defaults to `SERVER_EMAIL`
- `POST_FEATURE_REQUEST_URL` - url to post feature requests to
- `DISABLE_FEATURE_REQUEST` - if `True` will disable the feature request form
- `DISABLE_HELP_MENU` - if `True` will disable the help menu in the lower right corner
- `DISABLE_CONTACT_US` - if `True` will disable the contact us form and link
- `DOCS_URL` - url to the documentation
- `LEGAL_URL` - url to the legal page
- `TERMS_OF_SERVICE_URL` - url to the terms of service page
- `PDB_OAUTH_PROMPT_LINK` - controls how call to action for linking a peeringdb account is displayed
    - `never` - never show the call to action
    - `no_asn` - only show if there are no ASN authorizations
    - `always` - always show if there are no linked PeeringDB accounts