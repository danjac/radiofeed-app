# Provisioning a cluster

The file `hetzner.sh` is a script that provisions a cluster of Hetzner Cloud servers. It uses the Hetzner Cloud API to create the servers and then installs the necessary software on them.

## Requirements

- A Hetzner Cloud account
- An API token for the Hetzner Cloud API with Read and Write permissions
- Terraform installed on your machine

## Usage

1. Set the following environment variables

```bash
export TF_VAR_hcloud_token="your-hcloud-token"
```

2. Initialize Terraform

```bash
terraform init
```

3. Preview the changes

```bash
terraform plan
```

4. Apply the changes

```bash
terraform apply -auto-approve
```

Once you have applied the changes, you will see the IP addresses of the servers that have been created including private IP addresses.

You can now go to the `ansible` directory and run the following command to install the necessary software on the servers. See `ansible/README.md` for more information.
