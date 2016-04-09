**Author(s):** A lot of the core code is from [Adam Novak's original version](https://github.com/ga4gh/schemas/pull/297). Malisa Smith added clusters, urls, colors, and header comments. License of the original (and derived) work is under LICENSE.txt.  
**Date of this version:** February 24, 2016

* * * * * * * * * *

Visualize (.avdl format) schema files as a UML diagram using Graphviz.

This project creates a schema UML diagram from a list of github URL's which end in .avdl.  
It uses python to construct a .dot file, which is read by Graphviz's dot program to make a .svg diagram.  
It is designed for use with ga4gh avro schema files, e.g. https://github.com/ga4gh/schemas/tree/master/src/main/resources/avro

### To create the diagram:

**1)** Install graphviz and python 2.7 (3.0 might also work)

http://www.graphviz.org/Download..php

**2)** Make sure you have the following files in the same directory:

make_uml.sh  
avpr2uml.py  
url_converter.py  

**3)** Additionally, you should have two manually assembled input files in the directory:

schema_urls (required)  
type_header_comments (You can delete or modify the contents if you don't like the header comments, but the file must still exist as dummy input)

The schema_urls file contains a list of github .avdl file urls, e.g.   https://github.com/ga4gh/schemas/blob/master/src/main/resources/avro/reads.avdl  
Until the ga4gh schema is finalized and the entire schema can be stored in one local directory, files for inclusion in the diagram are to be listed in schema_urls.

The type_header_comments file contains lines of tab-delimited descriptions of data types, e.g. ReferenceSet	a reference assembly, e.g. GRCh38

**4)** Finally, run:

sh make_uml.sh

### Example UML diagram  

[Here](https://cdn.rawgit.com/malisas/schema-uml/master/example_svgs/master_uml_2016-03-07.svg)

Grey clusters in image should are click-able when viewing raw svg.  

### Limitations

Some edges and data structures may need to be manually modified or added in the dot file. You should check to make sure all data structures are properly represented in the UML diagram.

Referential edge-finding between data-structure fields is based on "id" string matching, e.g. "analysisId" will point to "Analysis" object. Non-id references will not be found. Containments of objects are based on complete string matches to field types.

If there is more than one instance of a data structure with the same name (e.g. "Evidence" might appear twice in the input avro files), it will only be drawn once. Technically this should be illegal anyway. If you want to have two objects with the same name, you must manually edit the dot file. Two objects with the same name will also cause edge-finding problems.
