## Docker Service Failures After Reboot

You are a DevOps engineer working on an Ubuntu 22.04 server. After a routine reboot, the Docker daemon fails to start and the production web stack (nginx, app, db) is offline. Diagnose the issue, fix it, ensure Docker starts on boot with all containers restored, and produce an incident report.

### Environment Setup

A setup script is provided at `/app/setup.sh`. Run it first to simulate the broken environment:

```
cd /app && bash setup.sh
```

This script will:
- Install Docker (if not already installed)
- Create three containers: `prod-nginx`, `prod-app`, `prod-db`
- Simulate the post-reboot failure state where Docker cannot start normally

### Requirements

1. **Diagnose the Docker startup failure**: Identify why the Docker daemon cannot start. Check systemd unit status, journal logs, and any configuration issues.

2. **Fix the underlying issue**: Resolve whatever is preventing the Docker service from starting. After your fix, `systemctl start docker` must succeed and `docker ps` must work.

3. **Enable Docker on boot**: Configure Docker so it starts automatically on boot. The command `systemctl is-enabled docker` must return `enabled`.

4. **Restore all containers**: Ensure all three production containers (`prod-nginx`, `prod-app`, `prod-db`) are running. Configure them with `restart: unless-stopped` (or equivalent restart policy) so they survive future reboots. Verify with `docker ps` that all three are in "Up" state.

5. **Produce an incident report**: Write a plain-text incident report to `/app/incident_report.txt` containing:
   - A line starting with `Root Cause:` describing what prevented Docker from starting
   - A line starting with `Fix Applied:` describing the corrective action taken
   - A line starting with `Prevention:` describing what was done to prevent recurrence

### Verification Criteria

- `systemctl is-active docker` returns `active`
- `systemctl is-enabled docker` returns `enabled`
- `docker ps --format '{{.Names}}'` lists `prod-nginx`, `prod-app`, and `prod-db` (all running)
- Each container's restart policy is set to `unless-stopped` or `always` (verifiable via `docker inspect --format '{{.HostConfig.RestartPolicy.Name}}' <container>`)
- `/app/incident_report.txt` exists and contains the three required sections: `Root Cause:`, `Fix Applied:`, `Prevention:`
