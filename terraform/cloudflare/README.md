# Cloudflare CDN and SSL Configuration with Terraform

This directory contains Terraform configuration for setting up Cloudflare as a CDN and SSL/TLS provider for Radiofeed. This setup assumes your domain is registered with another DNS provider (e.g., Namecheap, GoDaddy) and you're using Cloudflare as a proxy for CDN and security features.

## What This Configures

- **DNS Records**: A record pointing to your Hetzner server
- **CDN**: Caching for static assets (/static/_) and media files (/media/_)
- **SSL/TLS**: Full SSL mode with automatic HTTPS redirects
- **Security**: Firewall rules, security headers, and DDoS protection
- **Performance**: HTTP/3, Brotli compression, early hints
- **Caching Rules**: Aggressive caching for static content

## Prerequisites

### 1. Cloudflare Account

Sign up for a free Cloudflare account at <https://www.cloudflare.com/>

### 2. Add Domain to Cloudflare

1. Log in to Cloudflare Dashboard
2. Click "Add a Site"
3. Enter your domain name (e.g., `example.com`)
4. Select the Free plan
5. Cloudflare will scan your existing DNS records

### 3. Update Nameservers

Cloudflare will provide you with nameservers like:

- `ada.ns.cloudflare.com`
- `tate.ns.cloudflare.com`

Update your nameservers at your domain registrar:

**For Namecheap:**

1. Log in to Namecheap
2. Go to Domain List → Manage
3. Find "Nameservers" section
4. Select "Custom DNS"
5. Enter Cloudflare nameservers
6. Save changes

**For other providers:** Check your registrar's documentation for updating nameservers.

DNS propagation can take 24-48 hours, but usually completes within a few hours.

### 4. Cloudflare API Token

Create an API token with all required permissions:

1. Go to: <https://dash.cloudflare.com/profile/api-tokens>
2. Click "Create Token"
3. Click "Create Custom Token" (do NOT use a template)
4. Configure permissions:
   - **Permissions** (all zone-level):
     - Zone → Zone → Edit
     - Zone → Zone Settings → Edit
     - Zone → DNS → Edit
     - Zone → Page Rules → Edit
     - Zone → Zone WAF → Edit
     - Zone → Transform Rules → Edit
   - **Zone Resources**:
     - Include → Specific zone → Select your domain
   - **Client IP Address Filtering** (optional): Leave as "Is in" with your IP for extra security
5. Click "Continue to summary"
6. Review permissions and click "Create Token"
7. Copy the token (you won't see it again!)

**Note**: All permissions are at the **Zone** level (not Account level), since this configuration manages zone-specific resources.

### 5. Hetzner Server IP

You need the public IP of your Hetzner server node. Get it from Hetzner Terraform:

```bash
cd ../hetzner
terraform output server_public_ip
```

### 6. Origin Certificates for Ansible

**Important:** You need Cloudflare Origin Certificates for the Ansible deployment.

Generate origin certificates:

1. Go to: Cloudflare Dashboard → SSL/TLS → Origin Server
2. Click "Create Certificate"
3. Select "Generate private key and CSR with Cloudflare"
4. Choose validity period (15 years recommended)
5. Click "Create"
6. Save both files:
    - **Certificate** → Save as `ansible/certs/cloudflare.pem`
    - **Private Key** → Save as `ansible/certs/cloudflare.key`

**Security Note:** Keep these files secure. Add `ansible/certs/` to `.gitignore` if not already ignored.

## Setup

### 1. Configure Terraform Variables

Copy the example variables file:

```bash
cd terraform/cloudflare
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` and set:

- `cloudflare_api_token` - Your Cloudflare API token
- `domain` - Your domain name (e.g., "example.com")
- `subdomain` - Subdomain for the app (e.g., "" for root, "app" for app.example.com)
- `server_ip` - Public IP of your Hetzner server node
- `enable_www_redirect` - Whether to redirect www to root domain (default: true)
- `mailgun_dkim_value` - Mailgun DKIM public key (optional, leave empty to skip Mailgun DNS setup)
- `mailgun_mx_servers` - Mailgun MX servers (optional, defaults to EU servers)
- `mailgun_spf_value` - Mailgun SPF record (optional, defaults to `v=spf1 include:mailgun.org ~all`)

**Important:** Never commit `terraform.tfvars` to version control (already in .gitignore).

### 2. Initialize Terraform

```bash
terraform init
```

### 3. Preview Changes

```bash
terraform plan
```

Review the resources that will be created:

- DNS A record for your domain/subdomain
- Zone settings (SSL, security, performance)
- Page rules for caching static assets
- Firewall rules
- Security headers

### 4. Apply Configuration

```bash
terraform apply
```

Type `yes` to confirm.

### 5. Verify DNS Status

Check that nameservers are active:

```bash
terraform output dns_status
```

Should return `"active"`. If it shows `"pending"`, your nameservers haven't propagated yet.

### 6. Save Origin Certificates

If you haven't already, save the Cloudflare Origin Certificates:

```bash
# From project root
mkdir -p ansible/certs

# Copy your downloaded certificates
cp ~/Downloads/cloudflare.pem ansible/certs/
cp ~/Downloads/cloudflare.key ansible/certs/

# Secure the files
chmod 600 ansible/certs/cloudflare.*
```

## Integration with Hetzner and Ansible

### Complete Deployment Flow

1. **Provision Hetzner infrastructure**:

    ```bash
    cd terraform/hetzner
    terraform apply
    SERVER_IP=$(terraform output -raw server_public_ip)
    ```

2. **Configure Cloudflare** (use the SERVER_IP from step 1):

    ```bash
    cd ../cloudflare
    # Edit terraform.tfvars with the server IP
    terraform apply
    ```

3. **Save Origin Certificates**:

    ```bash
    cd ../../
    # Download from Cloudflare Dashboard → SSL/TLS → Origin Server
    # Save to ansible/certs/cloudflare.pem and ansible/certs/cloudflare.key
    ```

4. **Generate Ansible inventory**:

    ```bash
    cd terraform/hetzner
    terraform output -raw ansible_inventory > ../../ansible/hosts.yml
    ```

5. **Deploy with Ansible**:

    ```bash
    cd ../../
    just apb site
    ```

Ansible will use the Cloudflare origin certificates to set up SSL/TLS on your K3s cluster.

## Mailgun DNS Configuration

Mailgun DNS records (MX, SPF, DKIM) are managed by Terraform and created automatically when `mailgun_dkim_value` is set.

### Setup

1. Log in to [Mailgun Dashboard](https://app.mailgun.com/) → **Sending** → **Domains** → **DNS Records**
2. Copy the DKIM public key value (the `k=rsa; p=...` string from the TXT record for `mta._domainkey.mg`)
3. Add to your `terraform.tfvars`:

    ```hcl
    mailgun_dkim_value = "k=rsa; p=MIIBIjANBgk..."
    ```

4. Run `terraform apply`

The MX servers default to Mailgun's EU servers (`mxa.eu.mailgun.org`, `mxb.eu.mailgun.org`). Override `mailgun_mx_servers` and `mailgun_spf_value` in `terraform.tfvars` if needed (e.g. for US servers).

### Verify in Mailgun

1. Return to Mailgun Dashboard → DNS Records
2. Click **Verify DNS Settings**
3. All records should show green checkmarks when verified

## What Gets Cached

- CSS files
- JavaScript files
- Font files

- Images

- Images (logos, icons)
- Edge TTL: 30 days
- Browser TTL: 30 minutes

## SSL/TLS Configuration

The Terraform configuration sets up:

- **SSL Mode**: Full (requires valid certificate on origin server)
- **Always Use HTTPS**: Automatic redirect from HTTP to HTTPS
- **Minimum TLS Version**: 1.2
- **TLS 1.3**: Enabled
- **Automatic HTTPS Rewrites**: Enabled

The origin server uses Cloudflare Origin Certificates, which are:

- Trusted by Cloudflare (not publicly trusted)
- Valid for 15 years (recommended)
- Used for Cloudflare ↔ Origin communication only

## Security Features

### Firewall Rules

- Block access to sensitive files (`.env`, `.git`, etc.)
- Block common WordPress exploit paths (not applicable but defensive)

### Security Headers

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: SAMEORIGIN`
- `Referrer-Policy: strict-origin-when-cross-origin`

### DDoS Protection

Cloudflare's free tier includes automatic DDoS protection.

## Performance Optimizations

- **HTTP/3**: Enabled (QUIC protocol)
- **Brotli Compression**: Enabled
- **Early Hints**: Enabled (HTTP 103 status)
- **HTTP/2**: Enabled
- **Rocket Loader**: Disabled (not compatible with HTMX/Alpine.js)

## Troubleshooting

### Error: "Could not find zone"

**Problem**: Domain not found in Cloudflare account.

**Solution**:

1. Verify domain is added to Cloudflare Dashboard
2. Check `domain` in `terraform.tfvars` matches exactly
3. Ensure API token has access to this zone

### Error: "Authentication error"

**Problem**: Invalid or insufficient API token permissions.

**Solution**:

1. Verify `cloudflare_api_token` in `terraform.tfvars` is correct
2. Check token has ALL required permissions (see section 4 above):
   - Zone: Zone (Edit), Zone Settings (Edit), DNS (Edit), Page Rules (Edit), Zone WAF (Edit), Transform Rules (Edit)
   - All permissions must be at the Zone level, not Account level
3. Verify token includes the specific zone in Zone Resources
4. If token was created with wrong permissions, delete the old token and create a new one with correct permissions

### Error: "ruleset already exists"

**Problem**: Cloudflare automatically creates one ruleset per phase per zone. These always exist, even on a brand new zone or after deletion. Terraform cannot create them — they must be imported into state first.

This is expected on first apply, or if local state is lost.

**Solution**:

1. Get your zone ID (if not already in state, run `terraform apply -target=data.cloudflare_zone.domain` first):

    ```bash
    ZONE_ID=$(terraform show -json | jq -r \
      '.values.root_module.resources[] | select(.address == "data.cloudflare_zone.domain") | .values.id')
    ```

2. List zone-level rulesets and their IDs:

    ```bash
    curl -s "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/rulesets" \
      -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
      | jq '.result[] | select(.kind == "zone") | {id, phase, name}'
    ```

3. Import each ruleset using the matching phase:

    ```bash
    # Use the id where phase = "http_request_firewall_custom"
    terraform import cloudflare_ruleset.zone_level_firewall "zone/$ZONE_ID/<ID>"

    # Use the id where phase = "http_response_headers_transform"
    terraform import cloudflare_ruleset.transform_response_headers "zone/$ZONE_ID/<ID>"
    ```

4. Run `terraform apply` as normal. Subsequent applies will work without re-importing, as long as the local state is preserved.

### DNS Status Shows "Pending"

**Problem**: Nameservers not updated at domain registrar.

**Solution**:

1. Check nameservers at your domain registrar
2. Update to Cloudflare nameservers (shown in Cloudflare Dashboard)
3. Wait for DNS propagation (up to 24-48 hours)

### SSL/TLS Errors After Deployment

**Problem**: Origin certificates not properly configured.

**Solution**:

1. Verify `ansible/certs/cloudflare.pem` and `cloudflare.key` exist
2. Check certificates are valid (not expired)
3. Ensure Ansible deployment completed successfully
4. Check K3s secret: `kubectl get secret cloudflare-origin-cert -n default`

### Site Not Accessible via HTTPS

**Checklist**:

1. Terraform applied successfully
2. DNS status is "active" (`terraform output dns_status`)
3. Origin certificates deployed via Ansible
4. Server firewall allows ports 80 and 443
5. Traefik is running on K3s cluster

### Cache Not Working

**Problem**: Static assets not being cached.

**Solution**:

1. Check page rules in Cloudflare Dashboard → Rules → Page Rules
2. Verify URLs match pattern (e.g., `example.com/static/*`)
3. Test cache headers: `curl -I https://example.com/static/test.css`
4. Look for `CF-Cache-Status` header

## Updating Configuration

### Change Server IP

If your Hetzner server IP changes:

```bash
# Update terraform.tfvars with new IP
terraform apply
```

### Modify Caching Rules

Edit `main.tf` and adjust the `cloudflare_page_rule` resources:

```hcl
resource "cloudflare_page_rule" "cache_static" {
  # ...
  actions {
    edge_cache_ttl = 86400  # Change to 1 day instead of 30
  }
}
```

Then apply:

```bash
terraform apply
```

### Add More Page Rules

Cloudflare Free tier includes 3 page rules. The current configuration uses 2, leaving 1 available.

## Removing Configuration

**Warning**: This will remove DNS records and caching configuration.

```bash
terraform destroy
```

Type `yes` to confirm.

**Note**: This does NOT remove your domain from Cloudflare or change your nameservers.

## Cloudflare Dashboard

After applying Terraform, you can view and modify settings in the Cloudflare Dashboard:

- **DNS**: <https://dash.cloudflare.com/> → Select domain → DNS
- **SSL/TLS**: → SSL/TLS
- **Firewall**: → Security → WAF
- **Page Rules**: → Rules → Page Rules
- **Caching**: → Caching → Configuration
- **Analytics**: → Analytics & Logs

## Using Different DNS Providers

This setup is designed to work with any DNS provider:

### Namecheap

1. Add domain to Cloudflare
2. Update nameservers in Namecheap: Domain List → Manage → Nameservers → Custom DNS
3. Enter Cloudflare nameservers

### GoDaddy

1. Add domain to Cloudflare
2. Update nameservers in GoDaddy: My Products → Domains → DNS → Nameservers → Change
3. Enter Cloudflare nameservers (custom)

### Google Domains / Squarespace

1. Add domain to Cloudflare
2. Update nameservers: Use custom name servers
3. Enter Cloudflare nameservers

Once nameservers are updated, Cloudflare handles all DNS management.

## Resources

- [Cloudflare Dashboard](https://dash.cloudflare.com/)
- [Cloudflare Docs](https://developers.cloudflare.com/)
- [Terraform Cloudflare Provider](https://registry.terraform.io/providers/cloudflare/cloudflare/latest/docs)
- [Origin Certificates Guide](https://developers.cloudflare.com/ssl/origin-configuration/origin-ca/)
- [Cloudflare SSL Modes](https://developers.cloudflare.com/ssl/origin-configuration/ssl-modes/)

## Support

For issues related to:

- Cloudflare configuration → Check this README
- Hetzner infrastructure → See `../hetzner/README.md`
- Application deployment → See `../../ansible/README.md`
