#!/bin/bash

# Dump the SQLite database to an SQL file
sqlite3 travel_info.db .dump > travel_info.sql

# Remove the original SQLite database file
rm travel_info.db 