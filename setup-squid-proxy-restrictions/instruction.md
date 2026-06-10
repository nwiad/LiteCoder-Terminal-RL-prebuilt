## Ubuntu Squid Proxy Server with Time and IP Restrictions

Set up a Squid HTTP/HTTPS proxy server on Ubuntu that restricts access based on client IP subnet and time of day, then verify the configuration.

### Requirements

1. **Install Squid**
   - Update the package index and install `squid`.
   - Squid configuration file: `/etc/squid/squid.conf`

2. **Backup Original Configuration**
   - Copy the original Squid configuration to `/etc/squid/squid.conf.bak` before making any changes.

3. **Configure Access Control Lists (ACLs)**
   - Define an ACL named `company_net` for the subnet `10.0.0.0/24`.
   - Define a time-based ACL named `work_hours` that permits access Monday through Friday, 09:00–18:00.
   - Both ACLs must appear in `/etc/squid/squid.conf`.

4. **Configure Access Rules**
   - Add an `http_access allow` rule that requires both `company_net` AND `work_hours` to be satisfied simultaneously.
   - Add an `http_access deny all` rule to block all other traffic.
   - Squid must listen on the default port `3128`.

5. **Start and Verify Squid**
   - Start (or restart) the Squid service.
   - Verify that Squid is running and listening on port `3128`.

6. **Test the Proxy**
   - Install `curl` if not already present.
   - Run the following three test scenarios using curl through the proxy (`http://localhost:3128`) and record results:
     - **Test 1 – Allowed access:** A request from the allowed subnet during working hours. This should succeed (HTTP 200 or a valid response).
     - **Test 2 – Denied by IP:** A request from a disallowed subnet (e.g., `192.168.1.0/24`). This should be denied (HTTP 403).
     - **Test 3 – Denied by time:** A request outside working hours. This should be denied (HTTP 403).

7. **Write Test Results**
   - Write a JSON file to `/app/test_results.json` with the following structure:
     ```json
     {
       "squid_installed": true,
       "config_backup_exists": true,
       "acl_company_net_defined": true,
       "acl_work_hours_defined": true,
       "http_access_rules_configured": true,
       "squid_running": true,
       "squid_listening_on_3128": true,
       "test_allowed_access": "pass",
       "test_denied_by_ip": "pass",
       "test_denied_by_time": "pass"
     }
     ```
   - Each boolean field should be `true` if the corresponding check passed, `false` otherwise.
   - Each `test_*` field should be `"pass"` if the test produced the expected result, `"fail"` otherwise.

8. **Clean Up**
   - Restore the original configuration from `/etc/squid/squid.conf.bak` back to `/etc/squid/squid.conf`.
   - Stop the Squid service.

### Notes
- The container environment may not have systemd; use appropriate service management commands (e.g., `service squid start` or start Squid directly).
- For Test 2 and Test 3, simulate the conditions as closely as possible within the container (e.g., manipulating Squid config temporarily or using Squid's test/debug capabilities).
- All file paths are absolute. The working directory is `/app`.
