#!/usr/bin/env python2.7
"""
Authors: Adam Novak and Malisa Smith

avpr2uml.py: make UML diagrams from Avro AVPR files (which you can easily
generate from AVDL files). Inclusion of other types will be detected and turned
into the appropriate UML edges. ID references will be created if the referencee
has an "id" field, and the referencer has a referenceeNameId(s) field. Some
attempt is made to fuzzy-match referencers to referencees, but it is not perfect
and may require manual adjustment of the resulting edges.

Re-uses sample code and documentation from
<http://users.soe.ucsc.edu/~karplus/bme205/f12/Scaffold.html>
"""

import argparse, sys, os, itertools, re, json, textwrap
import url_converter

def parse_args(args):
    """
    Takes in the command-line arguments list (args), and returns a nice argparse
    result with fields for all the options.
    Borrows heavily from the argparse documentation examples:
    <http://docs.python.org/library/argparse.html>
    """

    # The command line arguments start with the program name, which we don't
    # want to treat as an argument for argparse. So we remove it.
    args = args[1:]

    # Construct the parser (which is stored in parser)
    # Module docstring lives in __doc__
    # See http://python-forum.com/pythonforum/viewtopic.php?f=3&t=36847
    # And a formatter class so our examples in the docstring look good. Isn't it
    # convenient how we already wrapped it to 80 characters?
    # See http://docs.python.org/library/argparse.html#formatter-class
    parser = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    # Now add all the options to it
    # Note: avprs is now an optional argument. One of --avprs or --clusters must be specified, however.
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--avprs", type=argparse.FileType("r"), default=None, nargs='*',
        help="the AVPR file(s) to read")
    group.add_argument("--clusters", type=str, default=None,
        help="List of original clusters/avdl files as a space-separated string, in imported order")
    parser.add_argument("--dot", type=argparse.FileType("w"),
        help="GraphViz file to write a UML diagram to")
    parser.add_argument("--urls", type=argparse.FileType("r"),
        help="File with schema url's")
    parser.add_argument("--type_comments", type=argparse.FileType("r"),
        help="tab-delimited file with type names and type header comments")


    return parser.parse_args(args)

def type_to_string(parsed_type, namespace=None, strip_namespace=False):
    """
    Given the JSON representation of a field type (a string naming an Avro
    primitive type, a string naming a qualified user-defiend type, a string
    naming a non-qualified user-defined type, a list of types being unioned
    together, or a dict with a "type" of "array" or "map" and an "items"
    defining a type), produce a string defining the type relative to the given
    namespace.

    If strip_namespace is specified, namespace info will be stripped out.

    """

    if isinstance(parsed_type, list):
        # It's a union. Recurse on each unioned element.
        return ("union<" + ",".join([type_to_string(x, namespace,
            strip_namespace) for x in parsed_type]) + ">")
    elif isinstance(parsed_type, dict):
        # It's an array or map.

        if parsed_type["type"] == "array":
            # For an array we recurse on items
           recurse_on = parsed_type["items"]
        elif parsed_type["type"] == "map":
            # For a map, we recurse on values.
            recurse_on = parsed_type["values"]
        else:
            # This is not allowed to be a template.
            raise RuntimeError("Invalid template {}".format(
                parsed_type["type"]))

        return (parsed_type["type"] + "<" +
            type_to_string(recurse_on, namespace, strip_namespace) + ">")
    elif parsed_type in ["int", "long", "string", "boolean", "float", "double",
        "null", "bytes"]:
        # If it's a primitive type, return it.
        return parsed_type
    elif "." in parsed_type:
        # It has a dot, so assume it's fully qualified. TODO: Handle partially
        # qualified types, where we have to check if this type actually exists.

        parts = parsed_type.split(".")

        parsed_namespace = ".".join(parts[:-1])

        if strip_namespace or parsed_namespace == namespace:
            # Pull out the namespace, sicne we don't want/don't need it
            parsed_type = [-1]

        return parsed_type
    else:
        # Just interpret it in our namespace. Don't fully qualify it.

        # Then give back the type name
        return parsed_type

def find_user_types(parsed_type, namespace=None):
    """
    Given the JSON representation of a field type (a string naming an Avro
    primitive type, a string naming a qualified user-defiend type, a string
    naming a non-qualified user-defined type, a list of types being unioned
    together, or a dict with a "type" of "array" or "map" and an "items"
    defining a type), yield all of the user types it references.

    """

    if isinstance(parsed_type, list):
        # It's a union.
        for option in parsed_type:
            # Recurse on each unioned element.
            for found in find_user_types(option, namespace):
                # And yield everything we find there.
                yield found
    elif isinstance(parsed_type, dict):
        # It's an array or map.

        if parsed_type["type"] == "array":
            # For an array we recurse on items
           recurse_on = parsed_type["items"]
        elif parsed_type["type"] == "map":
            # For a map, we recurse on values.
            recurse_on = parsed_type["values"]
        else:
            # This is not allowed to be a template.
            raise RuntimeError("Invalid template {}".format(
                parsed_type["type"]))

        for found in find_user_types(recurse_on, namespace):
            # Yield everything we find in there.
            yield found
    elif parsed_type in ["int", "long", "string", "boolean", "float", "double",
        "null", "bytes"]:
        # If it's a primitive type, skip it.
        pass
    elif "." in parsed_type:
        # It has a dot, so assume it's fully qualified. TODO: Handle partially
        # qualified types, where we have to check if this type actually exists.
        yield parsed_type
    else:
        # Just interpret it in our namespace.

        if namespace is not None:
            # First attach the namespace if applicable.
            parsed_type = "{}.{}".format(namespace, parsed_type)

        # Then give back the type name
        yield parsed_type

def type_to_node(type_name):
    """
    Convert an Avro type name (with dots) to a GraphViz node identifier.

    """

    # First double underscores
    type_name = type_name.replace("_", "__")
    # Then turn dots into underscores
    type_name = type_name.replace(".", "_")

    return type_name

def type_to_display(type_name):
    """
    Convert an Avro fully qualified type name (with dots) to a display name.

    """

    # Get the thing after the last dot, if any.
    return type_name.split(".")[-1]

def dot_escape(label_content):
    """
    Escape the given string so it is safe inside a GraphViz record label. Only
    actually handles the caharcters found in Avro type definitions, so not
    general purpose.

    """

    return (label_content.replace("&", "&amp;").replace("<", "&lt;")
        .replace(">", "&gt;").replace("\"", "&quot;"))

def parse_avprs(avpr_files, cluster_order, url_file, type_comments_file):
    """
    Given an iterator of AVPR file objects to read, return three things: a dict
    from fully qualified type names to lists of (field name, field type) tuples,
    and a set of (container, containee) containment tuples, and a set of
    (referencer, referencee) ID reference tuples.

    Edit: Optional clusters can also be specified (in place of the specified avpr_files) and returned

    """

    # Holds a dict from cluster key to full url. The key corressponds to a key in clusters, e.g. Key: reads.avdl    Value: (the url)
    urls = {}

    # Holds a dict from type name to manually entered comment. e.g. Key: ExpressionUnits     Value: e.g. FPKM or TPM
    type_comments = {}

    # Holds the fields for each type, as lists of tuples of (name, type),
    # indexed by type. All types are fully qualified.
    fields = {}

    # Holds edge tuples for containment from container to contained.
    containments = set()

    # Holds a dict from lower-case short name to fully-qualified name for
    # everything with an "id" field.
    id_targets = {}

    # Holds a set of tuples of ID references, (fully qualified name of
    # referencer, lower-case target name)
    id_references = set()

    # Holds the field names from each original .avdl file, in order to draw one cluster of fields for each file
    # Key: cluster/file name     Value: tuple of field names
    clusters = {}

    # Fill in the urls dictionary.
    if url_file is not None:
        for url in url_file:
	    cooked_url = url_converter.get_cooked_url(url.strip())
	    url_key = cooked_url.split("/")[-1]
	    urls[url_key] = cooked_url

    # Fill in the type_comments dictionary
    if type_comments_file is not None:
        for type_comment in type_comments_file:
            type_comment_split = type_comment.split("\t")
            type_comments[type_comment_split[0]] = type_comment_split[1].strip()

    # Add types to clusters
    make_clusters = (cluster_order is not None)
    cluster_files = []
    if make_clusters:
	cluster_order_list = cluster_order.split()
        for cluster in cluster_order_list:
            current_cluster = open(os.path.join(os.getcwd(), 'schemas_avpr', cluster + ".avpr"), 'r')
            cluster_files.append(current_cluster)

    files_for_iteration = None
    if make_clusters:
        files_for_iteration = cluster_files
    else:
        files_for_iteration = avpr_files

    # For avpr_file in avpr_files:
    for avpr_file in files_for_iteration:
        # Load each protocol that we want to look at.
        protocol = json.load(avpr_file)

        # Grab the namespace if set
        protocol_namespace = protocol.get("namespace", None)

        #Define cluster key if applicable
        cluster_key = None
        if make_clusters:
            cluster_key = avpr_file.name.split("/")[-1][:-5] + ".avdl"  #e.g. path/to/common.avpr will become common.avdl

        for defined_type in protocol.get("types", []):
            # Get the name of the type
            type_name = defined_type["name"]

            type_namespace = defined_type.get("namespace", protocol_namespace)

            if type_namespace is not None:
                type_name = "{}.{}".format(type_namespace, type_name)

            #If make_clusters is set to True, then due to the order of files in cluster_files, a field should not get recorded in the wrong cluster because it is only recorded the first time it is seen.
            if fields.has_key(type_name):
                # Already saw this one.
                continue

            # Record this one as actually existing.
            fields[type_name] = []

            # Record the field in the correct cluster if applicable
            if make_clusters:
                clusters.setdefault(cluster_key, []).append(type_name)

#            print("Type {}".format(type_name))

            if defined_type["type"] == "record":
                # We can have fields.

                for field in defined_type["fields"]:
                    # Parse out each field's name and type
                    field_type = type_to_string(field["type"], type_namespace)
                    field_name = field["name"]

                    # Announce every field with its type
#                    print("\t{} {}".format(field_type, field_name))

                    # Record the field for the UML.
                    fields[type_name].append((field_name, field_type))

                    for used in find_user_types(field["type"], type_namespace):
                        # Announce all the user types it uses
#                        print("\t\tContainment of {}".format(used))

                        # And record them
                        containments.add((type_name, used, field_name))

                    if (field_name.lower() == "id" and
                        u"string" in field_type):

                        # This is a possible ID target. Decide what we would
                        # expect to appear in an ID reference field name.
                        target_name = type_to_display(type_name).lower()

                        if id_targets.has_key(target_name):
                            # This target is ambiguous.
                            id_targets[target_name] = None
#                            print("WARNING: ID target {} exists twice!")
                        else:
                            # Say it points here
                            id_targets[target_name] = type_name

#                        print("\t\tFound ID target {}".format(target_name))

                    elif (field_name.lower().endswith("id") or
                        field_name.lower().endswith("ids")):
                        # This is probably an ID reference

                        if field_name.lower().endswith("id"):
                            # Chop off exactly these characters
                            destination = field_name.lower()[0:-2]
                        elif field_name.lower().endswith("ids"):
                            # Chop off these instead. TODO: this is super ugly
                            # and regexes are better.
                            destination = field_name.lower()[0:-3]

                        # Announce and save the reference
#                        print("\t\tFound ID reference to {}".format(
#                            destination))
			#Edit 2-23-16: id_references tuples now contains a third index to aid in constructing edges from specific cells in type_name
                        id_references.add((type_name, destination, field_name))

    # Now we have to match ID references to targets. This holds the actual
    # referencing edges, as (from, to) fully qualified name tuples.
    references = set()

    for from_name, to_target, from_field_name in id_references:
        # For each reference

        if id_targets.has_key(to_target):
            # We point to something, what is it?
            to_name = id_targets[to_target]

            if to_name is None:
                # We point to something that's ambiguous
#                print("WARNING: Ambiguous target {} used by {}!".format(
#                    to_target, from_name))
                pass
            else:
                # We point to a real thing. Add the edge.
#                print("Matched reference from {} to {} exactly".format(
#                    from_name, to_name))
                references.add((from_name, to_name, from_field_name))

        else:
            # None of these targets matches exactly
#            print("WARNING: {} wanted target {} but it does not exist!".format(
#                from_name, to_target))

            # We will find partial matches, and save them as target, full name
            # tuples.
            partial_matches = []

            for actual_target, to_name in id_targets.iteritems():
                # For each possible target, see if it is a partial match
                if (actual_target in to_target or
                    to_target in actual_target):

                    partial_matches.append((actual_target, to_name))

            if len(partial_matches) == 1:
                # We found exactly one partial match. Unpack it!
                actual_target, to_name = partial_matches[0]

                # Announce and record the match
#                print("WARNING: Matched reference from {} to {} on partial "
#                    "match of {} and {}".format(from_name, to_name, to_target,
#                    actual_target))
                references.add((from_name, to_name, from_field_name))
            elif len(partial_matches) > 1:
                # Complain we got no matches, or too many
#                print("WARNING: {} partial matches: {}".format(
#                    len(partial_matches),
#                    ", ".join([x[1] for x in partial_matches])))
                pass



    return fields, containments, references, clusters, urls, type_comments

def write_graph_ORIGINAL(dot_file, fields, containments, references):
    """
    Given a file object to write to, a dict from type names to lists of (name,
    type) field tuples, a set of (container, containee) containment edges, and a
    set of (referencer, referencee) ID reference edges, and write a GraphViz
    UML.

    See <http://www.ffnn.nl/pages/articles/media/uml-diagrams-using-graphviz-
    dot.php>

    """

    # Start a digraph
    dot_file.write("digraph UML {\n")

    # Define node properties: shaped like UML items.
    dot_file.write("node [\n")
    dot_file.write("\tshape=record\n")
    dot_file.write("]\n")

    for type_name, field_list in fields.iteritems():
        # Put a node for each type.
        dot_file.write("{} [\n".format(type_to_node(type_name)))

        # Start out the UML body bit with the class name
        dot_file.write("\tlabel=\"{{{}".format(type_to_display(type_name)))

        for field_name, field_type in field_list:
            # Put each field. Escape the field types.
            dot_file.write("|{} : {}".format(field_name,
                dot_escape(field_type)))

        # Close the label
        dot_file.write("}\"\n")

        # And the node
        dot_file.write("]\n")

    # Define edge properties for containments
    dot_file.write("edge [\n")
    dot_file.write("\tdir=both\n")
    dot_file.write("\tarrowtail=odiamond\n")
    dot_file.write("\tarrowhead=none\n")
    dot_file.write("]\n")

    for container, containee, container_field_name in containments:
        # Now do the containment edges
        dot_file.write("{} -> {}\n".format(type_to_node(container),
            type_to_node(containee)))

    # Define edge properties for references
    dot_file.write("edge [\n")
    dot_file.write("\tdir=both\n")
    dot_file.write("\tarrowtail=none\n")
    dot_file.write("\tarrowhead=vee\n")
    dot_file.write("\tstyle=dashed\n")
    dot_file.write("]\n")

    for referencer, referencee, local_referencee in references:
        # Now do the reference edges
        dot_file.write("{} -> {}\n".format(type_to_node(referencer),
            type_to_node(referencee)))

    # Close the digraph off.
    dot_file.write("}\n")

def write_graph_with_clusters(dot_file, fields, containments, references, clusters, urls, type_comments):
    """
    Given a file object to write to, a dict from type names to lists of (name,
    type) field tuples, a set of (container, containee) containment edges, and a
    set of (referencer, referencee) ID reference edges, and write a GraphViz
    UML.

    See <http://www.ffnn.nl/pages/articles/media/uml-diagrams-using-graphviz-
    dot.php>

    """
    
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
    for type_name, field_list in fields.iteritems():

        dot_file.write("{} [label=<\n".format(type_to_node(type_name)))#type_to_display(type_name)))
        dot_file.write("<TABLE BORDER='0' CELLBORDER='1' CELLSPACING='0' CELLPADDING='4' bgcolor='#002060' color='#002060'>\n")
        dot_file.write("\t<TR>\n")
        dot_file.write("\t\t<TD COLSPAN='2' bgcolor='#79A6FF' border='3'><FONT POINT-SIZE='20' color='white'>{}</FONT>".format(type_to_display(type_name)))
        # Add option to specify description for header:
        if type_to_display(type_name) in type_comments:
            dot_file.write("<BR/><FONT POINT-SIZE='15' color='white'>{}</FONT>".format(break_up_comment(type_comments[type_to_display(type_name)])))
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
    for cluster_name, cluster_types in clusters.iteritems():
        # Use type_to_node to replace . with _
        dot_file.write("subgraph cluster_{} {{\n".format(type_to_node(cluster_name)))
        dot_file.write("\tstyle=\"rounded, filled\";\n")
        dot_file.write("\tcolor=lightgrey;\n")
        dot_file.write("\tnode [style=filled,color=white];\n")
        dot_file.write("\tlabel = \"{}\";\n".format(cluster_name))
        if cluster_name in urls:
            dot_file.write("\tURL=\"{}\";\n".format(urls[cluster_name]))
        #After all the cluster formatting, define the cluster types
        for cluster_type in cluster_types:
            dot_file.write("\t{};\n".format(type_to_node(cluster_type))) #cluster_type should match up with a type_name from fields
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
        dot_file.write("{}:{}:w -> {}\n".format(type_to_node(container),
                                                container_field_name, type_to_node(containee)))

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

    for referencer, referencee, local_referencee in references:
        # Now do the reference edges
        dot_file.write("{}:{}:w -> {}:id:w\n".format(type_to_node(referencer), local_referencee,
            type_to_node(referencee)))




    # Close the digraph off.
    dot_file.write("}\n")


def main(args):
    """
    Parses command line arguments, and does the work of the program.
    "args" specifies the program arguments, with args[0] being the executable
    name. The return value should be used as the program's exit code.
    """

    options = parse_args(args) # This holds the nicely-parsed options object

    # Parse the AVPR files and get a dict of (field name, field type) tuple
    # lists for each user-defined type, a set of (container, containee)
    # containment relationships, an a similar set of reference relationships.
    fields, containments, references, clusters, urls, type_comments = parse_avprs(options.avprs, options.clusters, options.urls, options.type_comments)

    if options.dot is not None:
        # Now we do the output to GraphViz format.
        if bool(clusters): #check if the clusters dictionary is empty...if it isn't, draw the clusters
            write_graph_with_clusters(options.dot, fields, containments, references, clusters, urls, type_comments)
        else:
            write_graph_ORIGINAL(options.dot, fields, containments, references)


if __name__ == "__main__" :
    sys.exit(main(sys.argv))
