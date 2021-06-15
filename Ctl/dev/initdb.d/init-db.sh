#!/bin/bash

set -e

CREATE_PG="aaactl ixctl prefixctl"


for each in $CREATE_PG; do
  # create user
  psql --username "$POSTGRES_USER" <<-EOSQL
    CREATE USER $each WITH PASSWORD '$POSTGRES_PASSWORD' CREATEDB;
EOSQL

  # create db as user
  createdb --username $POSTGRES_USER -O ixctl ixctl
done


#  psql -v ON_ERROR_STOP=1 --username "$each" <<-EOSQL
#    CREATE DATABASE $each;
#EOSQL
#    CREATE USER $each WITH PASSWORD '$POSTGRES_PASSWORD' CREATEDB;
#    CREATE DATABASE $each;
#    GRANT ALL PRIVILEGES ON DATABASE $each TO $each;
