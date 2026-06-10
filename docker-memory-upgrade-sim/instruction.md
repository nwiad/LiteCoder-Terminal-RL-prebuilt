## Ubuntu Memory Upgrade Simulation

Simulate a memory upgrade on a running Ubuntu Docker container without restarting, using cgroups v2 and systemd features.

**Technical Requirements:**
- Environment: Ubuntu Docker container with cgroups v2 and systemd
- Container name: `webapp`
- Memory upgrade: 1 GB → 2 GB
- Output files:
  - `/app/memory_upgrade_report.json` - verification report
  - `/app/monitor_memory.sh` - monitoring script

**Task Requirements:**

1. Verify cgroups v2 is enabled and container uses systemd
2. Identify current memory limit and usage for the `webapp` container
3. Create a memory-consuming test process inside the container
4. Dynamically increase container memory limit from 1 GB to 2 GB without restart
5. Verify the memory limit change is applied and recognized
6. Monitor memory usage before and after the upgrade
7. Test memory allocation up to the new limit

**Output Specifications:**

`/app/memory_upgrade_report.json` must contain:
```json
{
  "initial_memory_limit": "1073741824",
  "initial_memory_usage": "<bytes>",
  "new_memory_limit": "2147483648",
  "new_memory_usage": "<bytes>",
  "verification_status": "success|failed",
  "commands_used": ["<command1>", "<command2>", "..."],
  "timestamp": "<ISO 8601 timestamp>"
}
```

`/app/monitor_memory.sh` must be an executable bash script that:
- Displays current memory limit and usage for the `webapp` container
- Outputs in human-readable format (MB/GB)
- Can be run repeatedly to track changes

**Validation Criteria:**
- Memory limit successfully increased from 1 GB to 2 GB
- Container remains running throughout the process
- Memory allocation test confirms new limit is effective
- All output files are created with correct format
