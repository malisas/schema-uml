#!/usr/bin/env bash

# Author: Malisa Smith

# Download all the proto schema files into the schemas_proto folder
# First clean-up old files from previous runs
rm -rf schemas_proto/*
# Obtain the raw github url's if not raw already:
raw_schema_urls=$(python url_converter.py --getrawfromfile schema_urls)
for raw_url in ${raw_schema_urls};
do
    wget --timestamping --directory-prefix ./schemas_proto ${raw_url};
done
