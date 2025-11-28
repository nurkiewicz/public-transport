#!/bin/bash

# Recreate the SQLite database from the SQL dump
sqlite3 travel_info.db < travel_info.sql 