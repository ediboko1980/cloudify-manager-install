#!/bin/bash

set -e

if [ $# -lt 3 ]; then
    echo "Missing arguments."
    echo "Usage: $0 db_name username password"
    exit 1
fi

db_name=$1
stage_db_name="stage"
composer_db_name="composer"
user=$2
password=$3

function run_psql() {
    cmd=$1
    echo "Going to run: ${cmd}"
    psql -c "${cmd}"
}

function create_database() {
    db_name=$1
    run_psql "CREATE DATABASE $db_name"
}

function create_admin_user() {
    db=$1
    user=$2
    password=$3
    run_psql "CREATE USER $user WITH PASSWORD '$password';"
    if [ -n "$PGUSER" ]; then
      IFS='@'
      read -ra server_user <<< "$PGUSER"
      run_psql "GRANT $user TO $server_user;"
    fi
    run_psql "GRANT ALL PRIVILEGES ON DATABASE $db TO $user;"
    run_psql "ALTER USER $user CREATEDB;"
    run_psql "ALTER DATABASE $db OWNER TO $user;"
}

function create_stage_database() {
    db=$1
    user=$2
    run_psql "CREATE DATABASE $db"
    run_psql "GRANT ALL PRIVILEGES ON DATABASE $db TO $user;"
    run_psql "ALTER DATABASE $db OWNER TO $user;"
}

function create_composer_database() {
    db=$1
    user=$2
    run_psql "CREATE DATABASE $db"
    run_psql "GRANT ALL PRIVILEGES ON DATABASE $db TO $user;"
    run_psql "ALTER DATABASE $db OWNER TO $user;"
}

function possibly_revoke_role_from_user() {
    user=$1
    if [ -n "$PGUSER" ]; then
      IFS='@'
      read -ra server_user <<< "$PGUSER"
      run_psql "REVOKE $user FROM $server_user"
    fi
}

create_database ${db_name}
create_admin_user ${db_name} ${user} ${password}
create_stage_database ${stage_db_name} ${user}
create_composer_database ${composer_db_name} ${user}
possibly_revoke_role_from_user ${user}
