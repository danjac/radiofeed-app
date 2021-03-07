#! /bin/bash

# directory to save backups in, must be rwx by postgres user
BASE_DIR="/var/backups/dokku-postgres"
YMD=$(date "+%Y-%m-%d")
DIR="$BASE_DIR/$YMD"

# make dir if it doesn't exist
mkdir -p $DIR
cd $DIR

# make database backup for all dbs
dbs=($(dokku postgres:list | awk 'NR>1{ print $1 }'))
for APP in "${dbs[@]}"
do
  dokku postgres:export $APP > "$DIR/$APP-db.sql"
done

# delete backup files older than 7 days
OLD=$(find $BASE_DIR -type d -mtime +7)
if [ -n "$OLD" ] ; then
  echo deleting old backup files: $OLD
  echo $OLD | xargs rm -rfv
fi
