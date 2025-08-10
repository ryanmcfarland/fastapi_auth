# DB Migrations - go-migrate

## install go

wget https://go.dev/dl/go1.24.2.linux-amd64.tar.gz

```bash
sudo cp -r go /usr/local/go1.24.1
```

export GOROOT=/usr/local/go1.24.1
export GOPATH=$HOME/go
export PATH=$GOPATH/bin:$GOROOT/bin:$PATH

```bash
go version
go version go1.24.2 linux/amd64
```

```bash
go install -tags 'postgres' github.com/golang-migrate/migrate/v4/cmd/migrate@latest
```

## go-migrate - basics

https://github.com/golang-migrate/migrate/blob/master/cmd/migrate/README.md

```bash
migrate create -ext sql -dir migrations -seq create_users_table
```

Note: Go uses the following datetime as its way to work with dates: https://stackoverflow.com/questions/20234104/how-to-format-current-time-using-a-yyyymmddhhmmss-format

```bash
migrate create -ext sql -dir migrations -format 20060102150405 create_users_table
```

To run / apply a version:

```bash
migrate -database YOUR_DATABASE_URL -path PATH_TO_YOUR_MIGRATIONS up
```

or `goto` a specific version:

```bash
migrate -path=./migrations -database=$DATABASE goto <migration number>
```

## Example

migrate -database postgresql://{username}:{password}@{hostname}:{port}/{database}?sslmode=disable -path db/migrations up

`?sslmode=disable` -> required due to ssl disabled in personal dev docker

## Create Databases Basic Docker

- variables used for docker setup

POSTGRES_USER={username}
POSTGRES_PASSWORD={password}
POSTGRES_DB={database}

```bash
export PGPASSWORD='{password}';psql -h {hostname} -d {database} -U {username}
```

### Create seperate databases

```bash
sudo -u postgres psql
postgres=# create database mydb;
postgres=# create user myuser with encrypted password 'mypass';
postgres=# grant all privileges on database mydb to myuser;
```

Reference: https://medium.com/coding-blocks/creating-user-database-and-adding-access-on-postgresql-8bfcd2f4a91e

```sql
create database {database};
create user {username} with encrypted password {password};
grant all privileges on database insert to {username};
GRANT SELECT ON ALL TABLES IN SCHEMA public TO {username};
GRANT CREATE ON SCHEMA public TO '{username}';
```

### Basic Postgres Permissions

```sql
SELECT grantee, privilege_type, table_schema, table_name
FROM information_schema.role_table_grants
WHERE grantee = '{username}';
```

```sql
-- connect to postgres from admin user
psql -U postgres -d {database}

-- Allow user to create tables in 'public' schema
GRANT USAGE, CREATE ON SCHEMA public TO {username};

-- Allow user to read all existing tables
GRANT SELECT ON ALL TABLES IN SCHEMA public TO {username};

-- Allow user to read all future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO {username};
```

```sql
SELECT n.nspname AS schema,
r.rolname AS grantee,
has_schema_privilege(r.rolname, n.nspname, 'USAGE') AS has_usage,
has_schema_privilege(r.rolname, n.nspname, 'CREATE') AS has_create
FROM pg_namespace n
JOIN pg_roles r ON has_schema_privilege(r.rolname, n.nspname, 'USAGE')
OR has_schema_privilege(r.rolname, n.nspname, 'CREATE')
WHERE r.rolname = '{username}';
```
