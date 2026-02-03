# PostgreSQL Volume Setup Role

This Ansible role prepares the PostgreSQL data volume on the database node with the correct permissions for use with Kubernetes StatefulSets.

## Purpose

When using block storage volumes (e.g., Hetzner Cloud Volumes) for PostgreSQL data persistence, the volume must be:
1. Mounted on the database node
2. Have proper ownership (UID/GID 999 for PostgreSQL container)
3. Have secure permissions (0700 as required by PostgreSQL)

This role automates these steps.

## Requirements

- The target server must have the block storage volume attached
- The volume should be formatted (e.g., ext4)
- The role runs with elevated privileges (become: true)

## Variables

This role uses the `postgres_volume` variable defined in `hosts.yml`:

```yaml
postgres_volume: "/mnt/HC_Volume_104566943"  # Path where volume is mounted
```

## Usage

### Hetzner Cloud Volume Setup

1. **Create a volume in Hetzner Cloud:**
   ```bash
   hcloud volume create --name postgres-data --size 40 --location fsn1
   ```

2. **Attach the volume to your database server:**
   ```bash
   hcloud volume attach postgres-data --server database
   ```

3. **Format the volume (first time only):**
   ```bash
   # SSH to the database server
   mkfs.ext4 /dev/disk/by-id/scsi-0HC_Volume_<volume-id>
   ```

4. **Add to /etc/fstab for automatic mounting:**
   ```bash
   echo '/dev/disk/by-id/scsi-0HC_Volume_<volume-id> /mnt/HC_Volume_<volume-id> ext4 discard,nofail,defaults 0 0' | sudo tee -a /etc/fstab
   mount -a
   ```

5. **Set the volume path in hosts.yml:**
   ```yaml
   postgres_volume: "/mnt/HC_Volume_104566943"
   ```

6. **Run the playbook:**
   ```bash
   ansible-playbook -i hosts.yml site.yml
   # or just the deploy playbook
   ansible-playbook -i hosts.yml deploy.yml
   ```

## What This Role Does

1. **Creates the directory** at the specified path
2. **Sets ownership** to UID 999 and GID 999 (PostgreSQL user in the container)
3. **Sets permissions** to 0700 (owner read/write/execute only)
4. **Validates** write access with a test file
5. **Only runs** on nodes with `role: database`

## PostgreSQL Container User

The official PostgreSQL Docker image runs as:
- User: postgres
- UID: 999
- GID: 999

The hostPath volume in Kubernetes will use these IDs to access the data directory.

## Troubleshooting

### Permission Denied Errors

If PostgreSQL fails to start with permission errors:
1. Check the volume is mounted: `df -h | grep HC_Volume`
2. Check ownership: `ls -ld /mnt/HC_Volume_*`
3. Should show: `drwx------ 2 999 999`

### Volume Not Mounted

If the volume isn't mounted on boot:
1. Check /etc/fstab has the correct entry
2. Test with: `sudo mount -a`
3. Verify with: `df -h`

### SELinux Issues (if applicable)

If using SELinux, you may need to set the correct context:
```bash
sudo chcon -Rt svirt_sandbox_file_t /mnt/HC_Volume_*
```
