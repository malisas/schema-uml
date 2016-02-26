#!/usr/bin/env python2.7
import argparse, sys, os, re

"""
Author: Malisa Smith

This program converts github url's to and from the raw file format url, e.g.:

Raw url:
https://raw.githubusercontent.com/ga4gh/schemas/master/src/main/resources/avro/reads.avdl

Not-raw url:
https://github.com/ga4gh/schemas/blob/master/src/main/resources/avro/reads.avdl
"""

def parse_args(args):
    """
    Note: This function heavily borrows from Adam Novak's code: https://github.com/adamnovak/schemas/blob/autouml/contrib/avpr2uml.py

    <http://docs.python.org/library/argparse.html>
    """

    # The command line arguments start with the program name, which we don't
    # want to treat as an argument for argparse. So we remove it.
    args = args[1:]

    # Construct the parser (which is stored in parser)
    # See http://docs.python.org/library/argparse.html#formatter-class
    parser = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    # Now add all the options to it
    #Note: avprs is now an optional argument. One of --avprs or --clusters must be specified, however.
    parser.add_argument("--getraw", type=str,
        help="Convert a github url to its raw form")
    parser.add_argument("--getcooked", type=str,
        help="Convert a github raw url to its not-raw/cooked form")
    parser.add_argument("--getrawfromfile", type=argparse.FileType("r"),
        help="Convert a list of urls in a file into their raw form")
    parser.add_argument("--getcookedfromfile", type=argparse.FileType("r"),
        help="Convert a list of urls in a file into their non-raw/cooked form")

    return parser.parse_args(args)

def get_raw_url(url):
    if re.match("^https://raw\.githubusercontent\.com/", url): #the url is already raw
        return url
    else: #convert into raw format
        url_parts = re.match("^https://github\.com/(?P<user>[a-zA-Z0-9_\-]+)/(?P<repo>[a-zA-Z0-9_\-]+)/blob/(?P<url_end>.*$)", url)
        return "https://raw.githubusercontent.com/" + url_parts.group('user') + "/" + url_parts.group('repo') + "/" + url_parts.group('url_end')

def get_cooked_url(url):
    if re.match("^https://github\.com/", url): #the url is already "cooked"
        return url
    else: #convert into "cooked" format
        url_parts = re.match("^https://raw\.githubusercontent\.com/(?P<user>[a-zA-Z0-9_\-]+)/(?P<repo>[a-zA-Z0-9_\-]+)/(?P<url_end>.*$)", url)
        return "https://github.com/" + url_parts.group('user') + "/" + url_parts.group('repo') + "/blob/" + url_parts.group('url_end')

def get_raw_from_file(my_file):
    for url in my_file:
        print(get_raw_url(url.strip()))

def get_cooked_from_file(my_file):
    for url in my_file:
        print(get_cooked_url(url.strip()))

def main(args):
    """
    Parses command line arguments, and does the work of the program.
    "args" specifies the program arguments, with args[0] being the executable
    name. The return value should be used as the program's exit code.
    """

    options = parse_args(args)

    if options.getraw is not None:
        print(get_raw_url(options.getraw))
    elif options.getcooked is not None:
        print(get_cooked_url(options.getcooked))
    elif options.getrawfromfile is not None:
        get_raw_from_file(options.getrawfromfile)
    elif options.getcookedfromfile is not None:
        get_cooked_from_file(options.getcookedfromfile)

if __name__ == "__main__" :
    sys.exit(main(sys.argv))
