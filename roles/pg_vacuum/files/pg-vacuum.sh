#!/bin/bash

for v in `docker ps --format '{{.Names}}\t{{.Status}}' | grep postgres | awk '{ print $1 }'`
do
  echo $v
  NNN=$v
  docker exec -it $NNN vacuumdb --all -U postgres --full --analyze
done
