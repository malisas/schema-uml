#! /usr/bin/python

"""
Author: Malisa Smith

Make UML diagrams based on protocol buffers-described schemas. Outputs a .dot file to be used with GraphViz's dot program.

Instead of parsing the original schema .proto files, this program takes a 
FileDescriptorSet as input. A FileDescriptorSet is itself a protobuf-serialized message which contains information about the original schema files within it (defined here:
https://github.com/google/protobuf/blob/master/src/google/protobuf/descriptor.proto). See README for how to generate the FileDescriptorSet.
"""

import argparse, sys, os, itertools, re, textwrap
from descriptor_pb2 import FileDescriptorSet #note: uses proto2!!
#import url_converter

def parse_args(args):

    args = args[1:]
    parser = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument("--descriptor", type=argparse.FileType("rb"),
        help="File with FileDescriptorSet of original schema")
    parser.add_argument("--dot", type=argparse.FileType("w"),
        help="GraphViz file to write a UML diagram to")
    parser.add_argument("--type_comments", type=argparse.FileType("r"),
        help="tab-delimited file with type names and type header comments")

    return parser.parse_args(args)

#parse a message. Pass in all the dictionries to be updates, as well as the relevant message and its parent message name if applicable
# For now just parse the name, field, nested_type, and enum_type fields in DescriptorProto: https://github.com/google/protobuf/blob/master/src/google/protobuf/descriptor.proto#L92
# Might later also want to parse oneof_decl, but assume for now I won't be dealing with that.
def parse_message(cluster, fields, containments, nests, id_targets, id_references, clusters, message):#, parent=""):   seems like type_name might already contain parent??
    #track all the fields in the message
    fields[message.name] = []

    for field in message.field:
        fields[message.name].append((field.name, field.type))
        #deal with containments, id_targets, and id_references, if applicable.
        #Containments will be signified by a field.type of 11 (for TYPE_MESSAGE) or 14 (for TYPE_ENUM). I can determine the type of containment by looking at field.type_name
        if field.type == 11 or field.type == 14:
            containments.add((message.name, field.type_name, field.name))
        #id_targets are simply fields where field.name is "id"
        if field.name.lower() == "id":
            id_targets[message.name] = field.name.lower().split(".")[-1]
            #id_targets[field.name.lower().split(".")[-1]] = message.name#field.name
        #id_references are fields which end in id or ids
        elif field.name.lower().endswith("id") or field.name.lower().endswith("ids"):
            if field.name.lower().endswith("id"):
                destination = field.name.lower()[0:-2]
            elif field.name.lower().endswith("ids"):
                destination = field.name.lower()[0:-3]
            id_references.add((message.name, destination, field.name))

    for nested_type in message.nested_type:
        #Note: it seems you can define a nested message without actually using it in a field in the outer message. So, a nested_type is not necessarily a field.
        #fields[message.name].append((nested_type.name, 11)) #a nested_type is a message. field types in DescriptorProto uses 11 for TYPE_MESSAGE
        
        #the nested_type is nested within the message. So keep track of this edge in the nests variable
        nests.add((message.name, nested_type.name))
        #nested_type is itself a message, so recursively call this function.
        parse_message(cluster, fields, containments, nests, id_targets, id_references, clusters, nested_type)

    for enum_type in message.enum_type: #a nested Enum
        #I think we can consider the enum a nesting too
        nests.add((message.name, enum_type.name))
        #And define it as a top-level type. So it has a fields entry.
        for field in enum_type.value:
            fields[enum_type.name].append((field, 9))
        #Finally, add it to the cluster
        clusters[cluster.name].append(enum_type.name)

    #Add the name of the message as a type in the current cluster
    clusters[cluster.name].append(message.name)

def parse_cluster(cluster, fields, containments, nests, id_targets, id_references, clusters):
    
    clusters[cluster.name] = []

    #process all the enum-types in the cluster
    for enum in cluster.enum_type:
        #Track all the enum "fields"
        fields[enum.name] = []
        for field in enum.value:
            fields[enum.name].append((field, 9)) #an Enum field is a string. field types in DescriptorProto uses 9 for TYPE_STRING
        #Record the name of the enum as a type in the current cluster
        clusters[cluster.name].append(enum.name)

    #track all the message-types in the cluster
    for message in cluster.message_type:
        #recursively parse each message
        parse_message(cluster, fields, containments, nests, id_targets, id_references, clusters, message)
        #Note: the message will add itself to the cluster

#for now, returns fields, containments, and references (and clusters?), although in the future might want to also return type_comments and urls and clusters, etc...
def parse_descriptor(descriptor_file):
    descriptor = FileDescriptorSet()
    descriptor.MergeFromString(descriptor_file.read())

    # Holds the fields for each type, as lists of tuples of (name, type),
    # indexed by type. All types are fully qualified.
    fields = {}

    # Holds edge tuples for containment from container to contained.
    containments = set()

    # Holds edge tuples for nested type edges, from parent type to nested type.
    nests = set()

    # Holds a dict from lower-case short name to fully-qualified name for
    # everything with an "id" field. E.g. if Variant has an id, then key is "variant" and value is "Variant"
    id_targets = {}

    # Holds a set of tuples of ID references, (fully qualified name of
    # referencer, lower-case target name)
    id_references = set()

    # Holds the field names from each original .avdl file, in order to draw one cluster of fields for each file
    # Key: cluster/file name     Value: tuple of field names
    clusters = {}

    for cluster in descriptor.file:
        #Note: you can pass a dictionary into a function and modify the original since it still refers to the same location in memory I think? (you don't need to pass it back)
        parse_cluster(cluster, fields, containments, nests, id_targets, id_references, clusters)

    #printing. test!
    print("\n*********************\nPRINTING fields\n(name, type)\n*********************\n")
    print(fields)

    print("\n*********************\nPRINTING containments\n(message name, field type name, field name)\n*********************\n")
    print(containments)

    print("\n*********************\nPRINTING nests\nparent type, nested type\n*********************\n")
    print(nests)

    print("\n*********************\nPRINTING id_targets\n()\n*********************\n")
    print(id_targets)

    print("\n*********************\nPRINTING id_references\n*********************\n")
    print(id_references)

    print("\n*********************\nPRINTING clusters\n*********************\n")
    print(clusters)



    #Now match the id references to targets.


    #Now write the diagram to the dot file!













def main(args):
    options = parse_args(args) # This holds the nicely-parsed options object

    parse_descriptor(options.descriptor)

    #fields, containments, references, clusters, urls, type_comments = parse_descriptor(???, options.urls, options.type_comments)

    #if options.dot is not None:
    #    write_graph(options.dot, fields, containments, references)


if __name__ == "__main__" :
    sys.exit(main(sys.argv))
