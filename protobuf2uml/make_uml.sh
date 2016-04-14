#!/usr/bin/env bash

# Author: Malisa Smith

# Generate descriptor_pb2.py with protoc:
protoc descriptor.proto --python_out=.

# Remove any temporary files in the schemas_proto directory which have have been created as a result of editing, etc:
rm -rf schemas_proto/*~

# convert .proto files into a serialized FileDescriptorSet for input into descriptor2uml.py
cd schemas_proto
protoc -o MyFileDescriptorSet.pb *
cd ../

# Make the dot file which describes the UML diagram. The type_header_comments file can be empty (or you can remove the option altogether)
python descriptor2uml.py --descriptor ./schemas_proto/MyFileDescriptorSet.pb --dot uml.dot --type_comments type_header_comments --urls schema_urls

# Finally, draw the UMl diagram
dot uml.dot -T svg -o uml.svg
