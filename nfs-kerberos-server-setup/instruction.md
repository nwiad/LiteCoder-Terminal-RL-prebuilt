## Secure NFS Server Setup with Kerberos Authentication

Configure a secure Network File System (NFS) server on Ubuntu with Kerberos authentication to provide shared storage access to trusted client machines.

## Technical Requirements

- Operating System: Ubuntu (assume apt package manager)
- NFS Server: nfs-kernel-server package
- Kerberos: krb5-kdc, krb5-admin-server, krb5-user packages
- Shared directory: /app/nfs_share
- Kerberos realm: EXAMPLE.COM
- NFS service principal: nfs/nfs-server.example.com@EXAMPLE.COM

## Implementation Requirements

1. **Package Installation**: Install required packages for NFS server and Kerberos (nfs-kernel-server, krb5-kdc, krb5-admin-server, krb5-user)

2. **Kerberos Configuration**:
   - Configure Kerberos realm as EXAMPLE.COM
   - Create NFS service principal: nfs/nfs-server.example.com@EXAMPLE.COM
   - Export keytab to /etc/krb5.keytab

3. **NFS Server Configuration**:
   - Create shared directory at /app/nfs_share with permissions 755
   - Configure /etc/exports to export /app/nfs_share with Kerberos security (krb5p)
   - Export format: `/app/nfs_share *(rw,sync,no_subtree_check,sec=krb5p)`

4. **Service Management**:
   - Enable and start rpc-gssd service
   - Enable and start nfs-kernel-server service
   - Ensure services are configured to start on boot

5. **Verification Output**:
   - Write configuration summary to /app/nfs_config_summary.txt containing:
     - Kerberos realm name
     - NFS service principal
     - Shared directory path
     - Export configuration line
     - Status of rpc-gssd service (active/inactive)
     - Status of nfs-kernel-server service (active/inactive)
     - List of exported directories from `showmount -e localhost`

## Output Format

The /app/nfs_config_summary.txt file should contain:
```
Kerberos Realm: <realm_name>
NFS Principal: <principal_name>
Shared Directory: <directory_path>
Export Configuration: <export_line>
RPC-GSSD Status: <active|inactive>
NFS Server Status: <active|inactive>
Exported Directories:
<showmount output>
```
