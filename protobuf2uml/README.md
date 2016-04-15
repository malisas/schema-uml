**Date of this version:** April 14, 2016

* * * * * * * * * *

### Project Description

Visualize (.proto format) schema files as a UML diagram using Graphviz.

This project creates a schema UML diagram from a list of github URL's which end in .proto.  
It uses python to construct a .dot file, which is read by Graphviz's dot program to make a .svg diagram.  
It is designed around ga4gh protobuf schema files, e.g. https://github.com/ga4gh/schemas/tree/protobuf/src/main/proto/ga4gh

### To create the diagram:

**1)** Install graphviz, libprotoc, and python 3.0 (2.7 might work if you edit descriptor2uml.py to use dict.iteritems() instead of dict.items())

To install graphviz, `sudo apt-get install graphviz` should work.

Notes for installing protobuf:

As of April 2016, on Ubuntu v14.04 the following command installed an old version of protobuf: `sudo apt-get install protobuf-compiler`, so instead I download the [latest release](https://github.com/google/protobuf/releases/) and installed manually:

`wget https://github.com/google/protobuf/releases/download/v3.0.0-beta-2/protobuf-python-3.0.0-beta-2.tar.gz`

`tar -xvzf protobuf-python-3.0.0-beta-2.tar.gz`

`cd protobuf-3.0.0-beta-2/`

`sudo ./configure`  
`sudo make`  
`sudo make check`  
`sudo make install`  
`sudo ldconfig`  
`protoc --version`  

`cd python/`  

`python setup.py`  
`python setup.py build`  
`python setup.py test`  
`sudo python setup.py install`

(I referred to [here](http://www.confusedcoders.com/random/how-to-install-protocol-buffer-2-5-0-on-ubuntu-13-04) and [here](https://github.com/BVLC/caffe/issues/2092#issuecomment-98917616) for protobuf installation help)

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

**4)** Finally, run:

`sh make_uml.sh`