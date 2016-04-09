#!/usr/bin/env bash

# Authors: Adam Novak and Malisa Smith

# Download all the avdl schema files into the schemas_avdl folder
# First clean-up old files from previous runs
rm -rf schemas_avdl/*
rm -rf schemas_avpr/*
# Obtain the raw github url's if not raw already:
raw_schema_urls=$(python url_converter.py --getrawfromfile schema_urls)
# Note: This wget command will overwrite old versions of files upon re-download, but it will not delete old unwanted files.
for raw_url in ${raw_schema_urls};
do
    wget --timestamping --directory-prefix ./schemas_avdl ${raw_url};
done

######################################

if [ ! -f avro-tools.jar ]
then

    # Download the Avro tools
    curl -o avro-tools.jar  http://www.us.apache.org/dist/avro/avro-1.7.7/java/avro-tools-1.7.7.jar
fi

# Make a directory for all the .avpr files
mkdir -p schemas_avpr

for AVDL_FILE in ./schemas_avdl/*.avdl
do
    # Make each AVDL file into a JSON AVPR file.

    # Get the name of the AVDL file without its extension or path
    SCHEMA_NAME=$(basename "$AVDL_FILE" .avdl)

    # Decide what AVPR file it will become.
    AVPR_FILE="./schemas_avpr/${SCHEMA_NAME}.avpr"

    # Compile the AVDL to the AVPR
    java -jar avro-tools.jar idl "${AVDL_FILE}" "${AVPR_FILE}"

done

######################################

# Now sort .avdl file names in order of referral (by imports)
# This is done to help form clusters of records from each file.
avpr_import_order=$(
for f in ./schemas_avdl/*.avdl;
do 
    doc_name=`echo -n $f | sed -r 's/.\/schemas_avdl\/([[:alnum:]]*).avdl/\1/g'`;
    grep "import idl" $f | awk -v dn=$doc_name '{printf dn"\t"$3"\n"}' | sed -r 's/"([[:alnum:]]*).avdl";/\1/g';
    printf ${doc_name}"\t"${doc_name}"\n"
done | tsort | tac | awk -vORS=" " '{ print $1 }' | sed 's/ $//'
)

######################################

# You can still use the original function to make the DOT file using a list of the avprs 
# Note: You now need to declare --avprs because it is no longer a positional argument
# ./avpr2uml.py --avprs `ls ./schemas_avpr/* | grep -v method` --dot uml.dot

# Or make the DOT file using clusters, urls, colors, and header comments
./avpr2uml.py --clusters "${avpr_import_order}" --dot uml.dot --urls schema_urls --type_comments type_header_comments

dot uml.dot -T svg -o uml.svg
