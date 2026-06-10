## Secure PostgreSQL Deployment with TLS

Install and configure a PostgreSQL server with TLS encryption using a self-signed certificate, enforcing SSL for all remote connections.

### Requirements

1. **Install PostgreSQL**: Install the PostgreSQL server and client packages. Ensure the `psql` client and `pg_isready` utilities are available. The PostgreSQL service must be running after setup.

2. **Generate a Self-Signed TLS Certificate**:
   - Generate a private key and self-signed certificate for PostgreSQL.
   - Certificate Common Name (CN): `pg-server.local`
   - Key size: 2048-bit RSA
   - Validity: 365 days
   - Place the certificate file at the PostgreSQL data directory as `server.crt`.
   - Place the private key file at the PostgreSQL data directory as `server.key`.
   - The key file must be owned by the `postgres` user and have permissions `0600`.
   - The certificate file must be owned by the `postgres` user and have permissions `0600`.

3. **Configure PostgreSQL for SSL/TLS**:
   - Enable SSL in `postgresql.conf` by setting `ssl = on`.
   - Set `ssl_cert_file` to point to `server.crt`.
   - Set `ssl_key_file` to point to `server.key`.
   - PostgreSQL must be listening on all interfaces (`listen_addresses = '*'`).

4. **Create Database and User**:
   - Create a database named `devdb`.
   - Create a user named `devuser` with password `devpass123`.
   - Grant `devuser` all privileges on database `devdb`.

5. **Enforce SSL for Remote Connections**:
   - In `pg_hba.conf`, configure so that remote connections (non-localhost) for all users and databases require SSL by using `hostssl` entries.
   - Local (Unix socket) connections and localhost (127.0.0.1/32, ::1/128) connections may use `md5` or `scram-sha-256` authentication without requiring SSL.
   - There must be no `host` (non-SSL) entries that allow remote (non-localhost) TCP/IP connections.

6. **Verify the Setup**:
   - The PostgreSQL service must be running and accepting connections.
   - An SSL connection to `devdb` as `devuser` must succeed.
   - The SSL connection must show that TLS is active (e.g., `sslmode=require` connects successfully).

7. **Documentation**: Write a connection reference file to `/app/connection_info.txt` with the following exact format (one item per line):
   ```
   host=pg-server.local
   port=5432
   dbname=devdb
   user=devuser
   sslmode=require
   ```
