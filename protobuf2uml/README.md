**Date of this version:** April 14, 2016

* * * * * * * * * *

### Project Description

Visualize (.proto format) schema files as a UML diagram using Graphviz.

This project creates a schema UML diagram from a list of github URL's which end in .proto.  
It uses python to construct a .dot file, which is read by Graphviz's dot program to make a .svg diagram.  
It is designed around ga4gh protobuf schema files, e.g. https://github.com/ga4gh/schemas/tree/protobuf/src/main/proto/ga4gh

### To create the diagram:

**1)** Install graphviz, libprotoc, and python 3.0 (2.7 might work if you edit descriptor2uml.py to use dict.iteritems() instead of dict.items())

http://www.graphviz.org/Download..php
https://github.com/google/protobuf/releases

**2)** Make sure you have the following files in the same directory:

make_uml.sh  
descriptor2uml.py  
url_converter.py  
descriptor.proto  

**3)** Additionally, you should have two manually assembled input files in the directory:

schema_urls (required for automatic download and if you want links in svg)  
type_header_comments (You can delete or modify the contents if you don't like the header comments, but the file should still exist as dummy input)

The schema_urls file contains a list of github .proto file urls.  
The type_header_comments file contains lines of tab-delimited descriptions of data types, e.g.  
`ReferenceSet	a reference assembly, e.g. GRCh38`

**4)** Download .proto files of the schema you want to display

You can do this automatically with `sh dl_schemas.sh`, or you can manually download the .proto files into the `schemas_proto` directory.

**5)** (If applicable) Manually remove all user-defined package references from schema files

If one or more of your .proto files are importing from user-defined packages, they will likely not be able to find each other and the `protoc -o MyFileDescriptorSet.pb *` command in `make_uml.sh` will not work.

* The following import statement is fine because it is not a user-defined package: `import "google/protobuf/struct.proto";`   
* However, the following import statement will not work because of reasons discussed [here](http://stackoverflow.com/a/5439189): `import "ga4gh/common.proto";`  
* Therefore, change all such import statements to the following (i.e. remove everything but the file-name): `import "common.proto";`
* (If you really don't want to modify your .proto files, you can change the directory structure to reflect the imports and specify a proto_path to the directory when running protoc in `make_uml.sh`, as discussed in the above link)

**6)** Finally, run:

`sh make_uml.sh`