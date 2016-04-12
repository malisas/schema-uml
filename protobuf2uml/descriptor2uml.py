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

#check the "message" to see if it is a trivial map.
def is_trivial_map(nested_type):
    #I am defining a trivial map to be a message with a nested_type.name that ends in "Entry". With two fields, "key" and "value". The "value" field has a type that is not 11 (and a list) or 14.
    if nested_type.name.endswith("Entry") and len(nested_type.field) == 2 and nested_type.field[0].name == "key" and nested_type.field[1].name == "value" and not ((nested_type.field[1].type == 11 and not nested_type.field[1].type_name == ".google.protobuf.ListValue") or nested_type.field[1] == 14):
        return True
    else:
        return False    

#parse a message. Pass in all the dictionries to be updates, as well as the relevant message and its parent message name if applicable
# For now just parse the name, field, nested_type, and enum_type fields in DescriptorProto: https://github.com/google/protobuf/blob/master/src/google/protobuf/descriptor.proto#L92
# Might later also want to parse oneof_decl, but assume for now I won't be dealing with that.
def parse_message(cluster, fields, containments, nests, id_targets, id_references, clusters, message):
    #track all the fields in the message
    fields[message.name] = []

    for field in message.field:
        fields[message.name].append((field.name, field.type))
        #deal with containments, id_targets, and id_references, if applicable.
        #Containments will be signified by a field.type of 11 (for TYPE_MESSAGE) or 14 (for TYPE_ENUM). I can determine the type of containment by looking at field.type_name
        #Note: maps will also come up as type 11 and will have a field.type_name of something like .bmeg.Feature.AttributesEntry where the actual field name is attributes
        if field.type == 11 or field.type == 14:
            # We are likely adding containments of trivial maps, e.g. ('VariantCallEffect', 'InfoEntry', 'info'). 
            # The edge is only drawn if the map/message itself is processed fully using parse_message(), however. And, it will only be processed
            # if it is not a trivial map. (see how nested_types are dealt with further down). When drawing containment edges, the program checks if the
            # field type_name is a key in the fields dictionary.
            containments.add((message.name, field.type_name.split(".")[-1], field.name))
        #id_targets are simply fields where field.name is "id"
        if field.name.lower() == "id":
            id_targets[message.name.lower()] = (message.name, field.name.lower().split(".")[-1])
            #id_targets[field.name.lower().split(".")[-1]] = message.name#field.name
        #id_references are fields which end in id or ids
        elif field.name.lower().endswith("id") or field.name.lower().endswith("ids"):
            if field.name.lower().endswith("id"):
                destination = field.name.lower()[0:-2]
            elif field.name.lower().endswith("ids"):
                destination = field.name.lower()[0:-3]
            destination = destination.replace("_", "")
            id_references.add((message.name, destination, field.name))

    for nested_type in message.nested_type:
        #Note: it seems you can define a nested message without actually using it in a field in the outer message. So, a nested_type is not necessarily used in a field.
        #fields[message.name].append((nested_type.name, 11)) #a nested_type is a message. field types in DescriptorProto uses 11 for TYPE_MESSAGE
        
        # Note: according to https://developers.google.com/protocol-buffers/docs/proto#backwards-compatibility 
        # maps are sent as messages (not map-types) "on the wire". We don't want to draw nodes for nested types that are trivial maps of string to string.
        # So, check if we want to process the nested_type further:
        if not is_trivial_map(nested_type):
            #the nested_type is nested within the message. So keep track of this edge in the nests variable
            #nests.add((message.name, nested_type.name)) #for now actually don't bother drawing edges for nests.

            #nested_type is itself a message, so recursively call this function.
            parse_message(cluster, fields, containments, nests, id_targets, id_references, clusters, nested_type)

    for enum_type in message.enum_type: #a nested Enum
        #we can consider the enum a nesting too
        #nests.add((message.name, enum_type.name)) #For now don't bother with drawing edges for xnests
        #And define it as a top-level type. So it has a fields entry.
        fields[enum_type.name] = []
        for field in enum_type.value:
            fields[enum_type.name].append((field.name, 9))
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
            fields[enum.name].append((field.name, 9)) #an Enum field is a string. field types in DescriptorProto uses 9 for TYPE_STRING
        #Record the name of the enum as a type in the current cluster
        clusters[cluster.name].append(enum.name)

    #track all the message-types in the cluster
    for message in cluster.message_type:
        #recursively parse each message
        parse_message(cluster, fields, containments, nests, id_targets, id_references, clusters, message)
        #Note: the message will add itself to the cluster

def write_graph(fields, containments, nests, matched_references, clusters, type_comments_file, dot_file):

    # Parse type_comments_file if applicable
    type_comments = {}
    if type_comments_file is not None:
        for type_comment in type_comments_file:
            type_comment_split = type_comment.split("\t")
            type_comments[type_comment_split[0]] = type_comment_split[1].strip()

    # Breaks up a comment string so no more than ~57 characters are on each line
    def break_up_comment(comment):
        wrapper = textwrap.TextWrapper(break_long_words = False, width = 57)
        return "<BR/>".join(wrapper.wrap(comment))

    # Start a digraph
    dot_file.write("digraph UML {\n")

    # Define node properties: shaped like UML items.
    dot_file.write("node [\n")
    dot_file.write("\tshape=plaintext\n")
    dot_file.write("]\n\n")

    # Draw each node/type/record as a table
    for type_name, field_list in fields.items(): #python 2.x uses dict.iteritems() but python 3.x uses dict.items()

        dot_file.write("{} [label=<\n".format(type_name))#type_to_display(type_name)))
        dot_file.write("<TABLE BORDER='0' CELLBORDER='1' CELLSPACING='0' CELLPADDING='4' bgcolor='#002060' color='#002060'>\n")
        dot_file.write("\t<TR>\n")
        dot_file.write("\t\t<TD COLSPAN='2' bgcolor='#79A6FF' border='3'><FONT POINT-SIZE='20' color='white'>{}</FONT>".format(type_name))

        # Add option to specify description for header:
        if type_name in type_comments:
            dot_file.write("<BR/><FONT POINT-SIZE='15' color='white'>{}</FONT>".format(break_up_comment(type_comments[type_name])))

        dot_file.write("</TD>\n")
        dot_file.write("\t</TR>\n")


        # Now draw the rows of fields for the type. A field_list of [a, b, c, d, e, f, g] will have [a, e] in row 1, [b, f] in row 2, [c, g] in row 3, and just [d] in row 4
        num_fields = len(field_list)
        for i in range(0, num_fields//2 + num_fields%2):
            # Draw one row.
            dot_file.write("\t<TR>\n")
			# Port number and displayed text will be the i'th field's name
            dot_file.write("\t\t<TD align='left' port='{}'><FONT color='white'>- {}</FONT></TD>\n".format(field_list[i][0], field_list[i][0])) 
            if (num_fields%2) == 1 and (i == num_fields//2 + num_fields%2 - 1):
                # Don't draw the second cell in the row if you have an odd number of fields and it is the last row
                pass
            else:
                dot_file.write("\t\t<TD align='left' port='{}'><FONT color='white'>- {}</FONT></TD>\n".format(field_list[num_fields//2 + num_fields%2 + i][0], field_list[num_fields//2 + num_fields%2 + i][0]))
            dot_file.write("\t</TR>\n")

        # Finish the table
        dot_file.write("</TABLE>>];\n\n")

    # Now define the clusters/subgraphs
    for cluster_name, cluster_types in clusters.items(): #python 2.x uses dict.iteritems() but python 3.x uses dict.items()
        # Use type_to_node to replace . with _
        dot_file.write("subgraph cluster_{} {{\n".format(cluster_name.replace(".", "_")))
        dot_file.write("\tstyle=\"rounded, filled\";\n")
        dot_file.write("\tcolor=lightgrey;\n")
        dot_file.write("\tnode [style=filled,color=white];\n")
        dot_file.write("\tlabel = \"{}\";\n".format(cluster_name.replace(".", "_")))

        #if cluster_name in urls:
        #    dot_file.write("\tURL=\"{}\";\n".format(urls[cluster_name]))

        #After all the cluster formatting, define the cluster types
        for cluster_type in cluster_types:
            dot_file.write("\t{};\n".format(cluster_type)) #cluster_type should match up with a type_name from fields
        dot_file.write("}\n\n")


    dot_file.write("\n// Define containment edges\n")
    # Define edge properties for containments
    dot_file.write("edge [\n")
    dot_file.write("\tdir=both\n")
    dot_file.write("\tarrowtail=odiamond\n")
    dot_file.write("\tarrowhead=none\n")
    dot_file.write("\tcolor=\"#C55A11\"\n")
    dot_file.write("\tpenwidth=2\n")
    dot_file.write("]\n\n")

    for container, containee, container_field_name in containments:
        # Now do the containment edges
        # Only write the edge if the containee is a top-level field in fields.
        if containee in fields:
            dot_file.write("{}:{}:w -> {}\n".format(container,
                                                    container_field_name, containee))

    dot_file.write("\n// Define references edges\n")
    # Define edge properties for references
    dot_file.write("\nedge [\n")
    dot_file.write("\tdir=both\n")
    dot_file.write("\tarrowtail=none\n")
    dot_file.write("\tarrowhead=vee\n")
    dot_file.write("\tstyle=dashed\n")
    dot_file.write("\tcolor=\"darkgreen\"\n")
    dot_file.write("\tpenwidth=2\n")
    dot_file.write("]\n\n")

    for referencer, referencer_field, referencee in matched_references:
        # Now do the reference edges
        dot_file.write("{}:{}:w -> {}:id:w\n".format(referencer, referencer_field,
            referencee))


    # Close the digraph off.
    dot_file.write("}\n")


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

    #Now match the id references to targets.
    matched_references = set() #will contain tuples of strings, i.e. (referencer, referencer_field, referencee)
    #id_targets_keys_lowercase = [key.lower() for key in id_targets.keys()]
    for id_reference in id_references:
        if id_reference[1] in id_targets:
            matched_references.add((id_reference[0], id_reference[2], id_targets[id_reference[1]][0]))

    return (fields, containments, nests, matched_references, clusters)
"""
    #printing. test!
    print("\n*********************\nPRINTING fields\n(parent-type-name: [(field-name, field-type)]\n*********************\n")
    print(fields)

    print("\n*********************\nPRINTING containments\n(message name, field type name, field name)\n*********************\n")
    print(containments)

    print("\n*********************\nPRINTING nests\n(parent type, nested type)\n*********************\n")
    print(nests)

    print("\n*********************\nPRINTING id_targets\n(target-type-lower: (target-type, id-format))\n*********************\n")
    print(id_targets)

    print("\n*********************\nPRINTING id_references\n(referer-name, referred-type-lower, referer-field)\n*********************\n")
    print(id_references)

    print("\n*********************\nPRINTING clusters\n[list of types in one cluster/file]\n*********************\n")
    print(clusters)

    print("\n*********************\nPRINTING matched_references\n(referencer, referencer_field, referencee)\n*********************\n")
    print(matched_references)
"""
    
def main(args):
    options = parse_args(args) # This holds the nicely-parsed options object

    (fields, containments, nests, matched_references, clusters) = parse_descriptor(options.descriptor)

    if options.dot is not None:
        #Now write the diagram to the dot file!
        write_graph(fields, containments, nests, matched_references, clusters, options.type_comments, options.dot)

if __name__ == "__main__" :
    sys.exit(main(sys.argv))
