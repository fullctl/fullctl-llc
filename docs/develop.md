
## fullctl services development instance

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

### Services

fullctl expects all used services to be cloned in it's parent dir. For example:

```
github.com/fullctl/
  fullctl/
  aaactl/
  ixctl/
  prefixctl/
```

### Database

This uses a common database server between fullctl services, each service still has it's own database.

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

### TODO

Decide whether to use a common `.env` file (like aaactl_web) or use one from the service directory (like ixctl_web).
