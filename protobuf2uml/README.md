**Date of this version:** April 12, 2016

* * * * * * * * * *

### Project Description

Visualize (.proto format) schema files as a UML diagram using Graphviz.

This project creates a schema UML diagram from a list of github URL's which end in .proto.  
It uses python to construct a .dot file, which is read by Graphviz's dot program to make a .svg diagram.  
It is designed around ga4gh protobuf schema files, e.g. https://github.com/ga4gh/schemas/tree/protobuf/src/main/proto/ga4gh

### To create the diagram:

**1)** Install graphviz and python 3.0 (2.7 might work if you edit descriptor2uml.py to use dict.iteritems() instead of dict.items())

http://www.graphviz.org/Download..php

**2)** Make sure you have the following files in the same directory:

make_uml.sh  
descriptor2uml.py  
url_converter.py  
descriptor.proto  

**3)** Additionally, you should have two manually assembled input files in the directory:

schema_urls (required)  
type_header_comments (You can delete or modify the contents if you don't like the header comments, but the file should still exist as dummy input)

The schema_urls file contains a list of github .proto file urls.  
The type_header_comments file contains lines of tab-delimited descriptions of data types, e.g.
`ReferenceSet	a reference assembly, e.g. GRCh38`

**4)** Finally, run:

sh make_uml.sh

NOTE: You will probably get at error at this point if one or more of your .proto files are importing from user-defined directories/packages. (assuming of course you listed the imported, user-defined .proto files in schema_urls)  
* The following import statement is fine because it is not a user-defined package: `import "google/protobuf/struct.proto";`   
* However, the following import statement will not work because of reasons discussed [here](http://stackoverflow.com/a/5439189): `import "ga4gh/common.proto";`  
* Therefore, change all such import statements to the following (i.e. remove everything but the file-name): `import "common.proto";`  
* (If you really don't want to modify your .proto files, you can change the directory structure to reflect the imports and specify a proto_path to the directory when running protoc, as discussed in the above link)

Then re-run the protoc command (from the schemas_proto directory) and the final two commands:

`protoc -o MyFileDescriptorSet.pb *`  
`python descriptor2uml.py --descriptor ./schemas_proto/MyFileDescriptorSet.pb --dot uml.dot --type_comments type_header_comments`  
`dot uml.dot -T svg -o uml.svg`
