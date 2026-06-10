## Automated User Account Lifecycle Management

Build a secure lifecycle management system that provisions, monitors, modifies, and retires user accounts with scheduling, logging, and automated auditing for temporary project-based workers.

### Technical Requirements

- **Language**: Bash scripting (compatible with Linux systems)
- **Input**: `/app/users.json` - User account definitions with project dates, roles, and quotas
- **Output**:
  - `/app/logs/lifecycle.log` - Structured JSON logs for all operations
  - `/app/audit/report.json` - Daily audit report with compliance metrics
  - `/app/notifications/alerts.json` - Critical event notifications

### Input Format

The `/app/users.json` file contains an array of user objects:

```json
{
  "users": [
    {
      "username": "jdoe",
      "full_name": "John Doe",
      "project_start": "2024-01-15",
      "project_end": "2024-06-30",
      "role": "developer",
      "disk_quota_mb": 5120,
      "groups": ["developers", "project_alpha"]
    }
  ]
}
```

**Fields:**
- `username`: System username (alphanumeric, lowercase)
- `full_name`: User's full name
- `project_start`: Start date (YYYY-MM-DD format)
- `project_end`: End date (YYYY-MM-DD format)
- `role`: One of: `developer`, `manager`, `analyst`, `admin`
- `disk_quota_mb`: Disk quota in megabytes
- `groups`: Array of group names for the user

### Output Format

**Lifecycle Log** (`/app/logs/lifecycle.log`):
Each operation must append a JSON line with:
```json
{"timestamp": "2024-01-15T10:30:00Z", "operation": "provision", "username": "jdoe", "status": "success", "details": "User created with role developer"}
```

**Audit Report** (`/app/audit/report.json`):
```json
{
  "report_date": "2024-01-15",
  "total_users": 25,
  "active_users": 20,
  "expired_accounts": 3,
  "quota_violations": 2,
  "operations_today": 15,
  "failed_operations": 0
}
```

**Alerts** (`/app/notifications/alerts.json`):
```json
{
  "alerts": [
    {
      "timestamp": "2024-01-15T10:30:00Z",
      "severity": "warning",
      "type": "quota_violation",
      "username": "jdoe",
      "message": "User exceeded 90% of disk quota"
    }
  ]
}
```

### System Requirements

1. **Provisioning**: Create users with role-based home directories (`/home/<role>/<username>`), assign groups, and set disk quotas
2. **Monitoring**: Track disk usage and generate alerts when users exceed 90% of quota
3. **Modification**: Support updating user roles, extending project end dates, and adjusting quotas via updated `/app/users.json`
4. **Retirement**: Archive user data to `/app/archives/<username>.tar.gz` and remove accounts when `project_end` date is passed
5. **Scheduling**: Implement daily automated checks (provide systemd timer configuration)
6. **Logging**: All operations must be logged to `/app/logs/lifecycle.log` with timestamp, operation type, username, status, and details
7. **Audit Reports**: Generate daily reports in `/app/audit/report.json` with metrics
8. **Notifications**: Write critical alerts to `/app/notifications/alerts.json`

### Edge Cases

- Handle users with past `project_end` dates (mark for retirement)
- Detect and alert on quota violations (>90% usage)
- Handle missing or malformed input data gracefully
- Log all errors with appropriate status codes
- Prevent duplicate user creation
