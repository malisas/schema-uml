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

# convert .proto files into a serialized FileDescriptorSet for input into descriptor2uml.py
cd schemas_proto
protoc -o MyFileDescriptorSet.pb *
cd ../

# NOTE: You will probably get at error at this point if one or more of your .proto files are importing
# from user-defined directories/packages. (assuming of course you listed the imported, user-defined .proto files in schema_urls)
# The following import statement is fine because it is not a user-defined package:
# 
# import "google/protobuf/struct.proto";
# 
# However, the following import statement will not work because of reasons discussed here: http://stackoverflow.com/a/5439189
# 
# import "ga4gh/common.proto";
# 
# Therefore, change all such import statements to the following (i.e. remove everything but the file-name):
#
# import "common.proto";
# 
# (If you really don't want to modify your .proto files, you can change the directory structure to reflect the imports and 
# specify a proto_path to the directory when running protoc, like discussed in the above link)
#
# Then re-run the protoc command and the following two commands:

# Make the dot file which describes the UML diagram. The type_header_comments file can be empty (or you can remove the option altogether)
python descriptor2uml.py --descriptor ./schemas_proto/MyFileDescriptorSet.pb --dot uml.dot --type_comments type_header_comments

# Finally, draw the UMl diagram
dot uml.dot -T svg -o uml.svg
