#!/bin/bash


APP_PATH="./src/"
APP="python3 $APP_PATH --port /dev/ttyAMA0 --pi --"

log_file=app_runner.log

curr_time=$(date "+%Y.%m.%d-%H.%M.%S")
echo "[$curr_time] rf-draw Started.." >> $log_file

until $APP; do
	curr_time=$(date "+%Y.%m.%d-%H.%M.%S")
    echo "[$curr_time] rf-draw crashed with exit code $?.  Respawning.." >> $log_file
    sleep 1
done

curr_time=$(date "+%Y.%m.%d-%H.%M.%S")
echo "**********[$curr_time] rf-draw exited with exit code 0**********" >> $log_file
