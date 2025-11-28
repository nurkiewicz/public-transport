#!/bin/bash

url="https://api.dane.gov.pl/media/resources/20220208/Adres_uniwersalny_2022.02.08.zip"
local_zip_filename="Adres_uniwersalny_2022.02.08.zip"
curl -o "$local_zip_filename" "$url"
unzip "$local_zip_filename"
rm "$local_zip_filename"
