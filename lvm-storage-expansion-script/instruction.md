## LVM Storage Expansion Script

Write a Bash script `/app/solution.sh` that performs LVM (Logical Volume Manager) storage expansion by adding a new disk `/dev/sdb` into an existing LVM setup and extending the root filesystem.

### Technical Requirements

- Language: Bash
- The script must be executable (`chmod +x`)
- The script must run as root
- Input disk: `/dev/sdb` (a raw, unpartitioned 10GB disk already attached to the system)
- The existing LVM setup uses a volume group and a logical volume mounted at `/`

### Script Behavior

The script must perform the following operations in order and write a structured report to `/app/output.json` upon completion:

1. **Partition the new disk**: Create a single partition on `/dev/sdb` spanning the entire disk, with partition type set to Linux LVM (type code `8e`). The resulting partition should be `/dev/sdb1`.

2. **Create a Physical Volume (PV)**: Initialize `/dev/sdb1` as an LVM physical volume using `pvcreate`.

3. **Extend the Volume Group (VG)**: Add the new physical volume to the existing volume group that contains the root filesystem. The script must auto-detect the VG name (do not hardcode it).

4. **Extend the Logical Volume (LV)**: Extend the logical volume mounted at `/` to use 100% of the newly available free space in the VG. The script must auto-detect the LV path (do not hardcode it).

5. **Resize the Filesystem**: Resize the filesystem on the root logical volume to fill the extended LV. The script must handle both ext4 (using `resize2fs`) and xfs (using `xfs_growfs`) filesystem types.

6. **Generate report**: Write `/app/output.json` with the final state.

### Output Specification

The file `/app/output.json` must be valid JSON with the following structure:

```json
{
  "partition": {
    "device": "/dev/sdb1",
    "type": "8e"
  },
  "pv": {
    "device": "/dev/sdb1",
    "vg_name": "<detected VG name>"
  },
  "vg": {
    "name": "<detected VG name>",
    "pv_count": <integer, total PV count after extension>
  },
  "lv": {
    "path": "<detected LV path, e.g. /dev/mapper/vgname-lvname>",
    "size_bytes": <integer, LV size in bytes after extension>
  },
  "filesystem": {
    "mount_point": "/",
    "type": "<ext4 or xfs>",
    "total_size_kb": <integer, total filesystem size in KB after resize>
  },
  "status": "success"
}
```

### Error Handling

- If `/dev/sdb` does not exist, the script must write `/app/output.json` with `"status": "error"` and an `"error"` field describing the issue, then exit with code 1.
- If no LVM volume group is found, the script must similarly report an error in the JSON and exit with code 1.
- The script must exit with code 0 on success.

### Constraints

- Do not hardcode volume group names, logical volume names, or filesystem types. All must be detected at runtime.
- The script must be idempotent-safe: if `/dev/sdb1` already exists as a PV, it should skip the partition/PV creation steps and continue.
- All numeric values in the JSON output must be integers (not strings).
