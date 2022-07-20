
## fullctl services development instance
[Poetry](https://python-poetry.org/) is a python package manager it can be acquired by following the instructions [here](https://python-poetry.org/docs/)
(for macOS run `curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python -`) later commands will assume that t is installed on your system

## Code Quality

Install pre-commit with (for running before push)
```sh
poetry run pre-commit install -t pre-push
```

Or manually run with
```sh
poetry run pre-commit run --all-files
```

## Poetry

To update package deps, use

```sh
poetry lock
poetry install
poetry run pre-commit clean
```

## Database

This uses a common database server between fullctl services, each service still has it's own database.

To start it separately:

```sh
poetry run Ctl/dev/compose.sh up postgres
```

#### Backups

Backup dev database
```sh
poetry run Ctl/dev/exec.sh postgres bash -c 'pg_dumpall -c -U ${POSTGRES_USER}' | xz > fulldb-$(date +%Y%m%d"-"%H%M%S).sql.xz
```

Restore:
```sh
cat $FILE | poetry run Ctl/dev/exec.sh postgres bash -c 'psql -U ${POSTGRES_USER}'
```
#### Snippets

```sh
# add psql
apk add postgresql-client

# on postgres for superuser
PGPASSWORD=$DATABASE_PASSWORD psql -h postgres -U $POSTGRES_USER

# service user
PGPASSWORD=$DATABASE_PASSWORD psql -h postgres -U $DATABASE_USER
```

Check perms on table

```sql
SELECT grantee, privilege_type FROM information_schema.role_table_grants WHERE table_name='django_migrations';
```

## Services

fullctl expects all used services to be cloned in it's parent dir. For example:

```
github.com/fullctl/
  fullctl/
  aaactl/
  ixctl/
  prefixctl/
```

To start individually, for example `aaactl`
semanage port -m -t http_port_t -p tcp 8001



```sh
# change the port it listens on if needed
# export AAACTL_PORT=7002
poetry run Ctl/dev/compose.sh up aaactl_web
```

## Developer Environment Setup

Please run the following command to checkout and setup the verious repositories and services that make up a complete fullctl dev environment.

```
git clone git@github.com:fullctl/fullctl
. fullctl/scripts/devenv-setup.sh
```

At some point the script will prompt you to create a user, this is your superuser account that will work accross all services. (managed in aaactl)

After the script is done running, you will have the database container up and running and all of the service containers built and migrated to the latest database schema.

At this point you will want to go through each service in order and follow its individual setup steps and start them up.

**Note:** services will authenticate users through oauth to aaactl, this **requires** HTTPS, we found nginx reverse proxies used with certbot ceritifcates to be the easiest way to provide https for our dev instances.

**CentOS7** sometimes seems to have an issue allowing one container to connect to another, see [this](https://stackoverflow.com/questions/39134551/centos-vm-with-docker-getting-host-unreachable-when-trying-to-connect-to-itself/39211891#39211891) and [this](https://github.com/moby/moby/issues/32138) for possible workarounds.

### aaactl

Follow [instructions](https://github.com/fullctl/aaactl/blob/prep-release/docs/deploy.md) for the points listed below:

**required setup**

- Setup internal API key
- Setup oauth2 provider

**optional setup**

- PeeringDB oauth
- Google oauth


### run aaactl

```
export AAACTL_PORT=7001
poetry run Ctl/dev/compose.sh up aaactl_web
```

Your aaactl instance should now be running on port 7001

### pdbctl

Follow [instructions](https://github.com/fullctl/pdbctl/blob/prep-release/docs/quickstart.md) for the points listed below:

**required setup**

- Authentication and accounts

### run pdbctl

```
export PDBCTL_PORT=7002
poetry run Ctl/dev/compose.sh up pdbctl_web
```

Your pdbctl instance should now be running on port 7002

### ixctl

Follow [instructions](https://github.com/fullctl/ixctl/blob/prep-release/docs/quickstart.md) for the points listed below:

**required setup**

- Authentication and accounts
- add `PDBCTL_URL` to pdbctl/Ctl/dev/.env - pointing at your pdbctl instance (e.g., https://localhost:7002)

### run ixctl

```
export IXCTL_PORT=7003
poetry run Ctl/dev/compose.sh up ixctl_web
```

Your ixctl instance should now be running on port 7003

### peerctl

Follow [instructions](https://github.com/fullctl/peerctl/blob/prep-release/docs/quickstart.md) for the points listed below:

**required setup**

- Authentication and accounts
- add `PDBCTL_URL` to pdbctl/Ctl/dev/.env - pointing at your pdbctl instance (e.g., https://localhost:7002)
- add `IXCTL_URL` to pdbctl/Ctl/dev/.env - pointing at your pdbctl instance (e.g., https://localhost:7003)

### run peerctl

```
export PEERCTL_PORT=7004
poetry run Ctl/dev/compose.sh up peerctl_web
```

Your peerctl instance should now be running on port 7004

### Bumping release

```sh
poetry run ctl version bump .
poetry lock
git commit -am "lock, bump version"
poetry run ctl deploy_dev
```

### TODO
