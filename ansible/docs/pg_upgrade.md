# Upgrading PostgreSQL

To upgrade PostgreSQL to a new **major** version, follow these steps:

1. In the `hosts.yml` file, add the new postgres version as `postgres_new_image` and the new data volume as `postgres_new_volume`.

For example:

```yaml
    postgres_new_image: "postgres:17.6-bookworm"
    postgres_new_volume: "/mnt/volumes/postgres_data_v17"
```

2. Ensure the new volume is accessible to the `database` node.
3. Run `just apb pg_upgrade`. This will create a new PostgreSQL container with the new version and new stateful set etc with label `postgres-upgrade-*`.
3. SSH into the server node.
4. Verify that the PostgreSQL statefulsets are running correctly.
5. Delete the deployments and cronjobs, to ensure no connections to the database during the upgrade:

```bash
kubectl delete deployment django-app
kubectl delete cronjobs -l app=django-cronjob
```

6. SSH into the server node and run the `./pg_upgrade.sh` script located in the home directory (assuming current postgres is `postgres-0` and new is `postgres-upgrade-0`: check and adjust as necessary):

```bash
./pg_upgrade.sh postgres-0 postgres-upgrade-0
```

This script will make a dump of the old database and restore it to the new database.

You can check the progress by viewing the logs of the new PostgreSQL pod:

```bash
kubectl logs statefulset/postgres-upgrade -f
```

You can also access the current and new database with psql and compare table sizes, constraints, indexes etc:

```bash
kubectl exec -it postgres-0 -- psql -U postgres -d postgres
```

```bash
kubectl exec -it postgres-upgrade-0 -- psql -U postgres -d postgres
```

```sql
SELECT
    schemaname AS schema,
    relname AS table_name,
    n_live_tup AS approx_row_count
FROM pg_stat_user_tables
ORDER BY n_live_tup DESC;
```

```sql
SELECT
    n.nspname AS schema,
    t.relname AS table_name,
    c.conname AS constraint_name,
    c.contype AS constraint_type,  -- p=primary key, f=foreign key, u=unique, c=check, etc.
    pg_get_constraintdef(c.oid) AS definition
FROM pg_constraint c
JOIN pg_class t ON c.conrelid = t.oid
JOIN pg_namespace n ON n.oid = t.relnamespace
WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
ORDER BY n.nspname, t.relname, c.conname;
```

```sql
SELECT
    n.nspname AS schema,
    t.relname AS table_name,
    i.relname AS index_name,
    pg_get_indexdef(i.oid) AS index_def
FROM pg_index x
JOIN pg_class t ON t.oid = x.indrelid
JOIN pg_class i ON i.oid = x.indexrelid
JOIN pg_namespace n ON n.oid = t.relnamespace
WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
ORDER BY n.nspname, t.relname, i.relname;
```

7. Once the upgrade is complete, update the `hosts.yml` file to set `postgres_image` to the new version and `postgres_volume` to the new volume e.g.:

```yaml
    postgres_image: "postgres:17.6-bookworm"
    postgres_volume: "/mnt/volumes/postgres_data_v17"
```

Also remove or comment out the `postgres_new_image` and `postgres_new_volume` entries.

8. Delete the stateful set, PV and service for the upgrade deployment:

```bash
    kubectl delete statefulset postgres-upgrade
    kubectl delete service postgres-upgrade
    kubectl delete pvc postgres-upgrade-pvc
    kubectl delete pv postgres-upgrade-pv
```
9. Run `just apb deploy` again to redeploy the Django application and cronjobs:

```bash
    kubectl get pods
    kubectl logs deployment/django-app
```
10. Verify that the application is functioning correctly with the new PostgreSQL version, and delete any old resources if necessary.
