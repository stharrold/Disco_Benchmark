#!/usr/bin/env python
"""
Download bz2 files from list and upload to Disco Distributed File System.

TODO:
- check disco v0.4.4
- less IO if bz2 in map reader
"""

from __future__ import print_function
import argparse
import urllib2
import os
import bz2
import sys
from disco.ddfs import DDFS

def download(url, file_out="download.out"):
    """
    Download a file from a URL.
    """
    # From http://stackoverflow.com/questions/4028697
    # /how-do-i-download-a-zip-file-in-python-using-urllib2
    try:
        print("Downloading:\n{url}\nto\n{file_out}".format(url=url, file_out=file_out))
        f_url = urllib2.urlopen(url)
        with open(file_out, 'wb') as f_out:
            f_out.write(f_url.read())
    except urllib2.HTTPError, e:
        print("HTTP Error:", e.code, url, file=sys.stderr)
    except urllib2.URLError, e:
        print("URL Error:", e.reason, url, file=sys.stderr)
    return None

def decompress_and_partition(file_bz2, file_out="decompress.out"):
    """
    Decompress bz2 files and partition with newlines every 100 KB.
    Due to a bug in disco v0.4.4 for uploading, pushing a long record as a blob corrupts the existing tag.
    Chunk does not work on records over 1MB.
    See: https://groups.google.com/forum/#!searchin/disco-dev/push$20chunk/disco-dev/i9LiNiLEQ7k/95fX2sC-dtQJ
    """
    (base, ext) = os.path.splitext(file_bz2)
    if ext != '.bz2':
        print(file_bz2)
        raise NameError("File extension not '.bz2'.")
    print(
        "Decompressing and partitioning:\n"
        +"{file_bz2}\nto\n{file_out}".format(file_bz2=file_bz2, file_out=file_out))
    # From http://stackoverflow.com/questions/16963352/decompress-bz2-files
    # and http://bob.ippoli.to/archives/2005/06/14/python-iterators-and-sentinel-values/
    with open(file_out, 'wb') as f_out, bz2.BZ2File(file_bz2, 'rb') as f_bz2:
        for data in iter(lambda : f_bz2.read(100*1024), b''):
            f_out.write(data)
            f_out.write(b"\n")
    return None

def main(file_in, tmp_dir, tag, delete):
    """
    Download bz2 files from list and upload to Disco.
    """
    with open(file_in, 'r') as f_in:

        # If Disco tag exists, delete it.
        # Don't add all-new data to an already existing tag.
        if DDFS().exists(tag=tag):
            print("WARNING: Overwriting Disco tag {tag}.".format(tag=tag), file=sys.stderr)
            DDFS().delete(tag=tag)

        for line in f_in:

            # Skip commented lines.
            if line.startswith('#'):
                continue

            # Remove newlines and name file from URL.
            url = line.strip()
            file_bz2 = os.path.join(tmp_dir, os.path.basename(url))
            # Download bz2 file if it doesn't exist.
            if os.path.isfile(file_bz2):
                print("Skipping download. File already exists:\n{file_bz2}".format(file_bz2=file_bz2))
            else:
                download(url=url, file_out=file_bz2)

            # Decompress and partition bz2 file if it doesn't exist.
            file_decom = os.path.splitext(file_bz2)[0]
            if os.path.isfile(file_decom):
                print("Skipping decompress and partition. "
                      +"File already exists:\n{file_decom}".format(file_decom=file_decom))
            else:
                decompress_and_partition(file_bz2=file_bz2, file_out=file_decom)

            # Load data into Disco Distributed File System.
            print("Loading into Disco:\n{file_in}".format(file_in=file_decom))
            try:
                DDFS().chunk(tag=tag, urls=[os.path.join('./', file_decom)])
            except ValueError as err:
                print("ValueError: " + err.message, file=sys.stderr)
                print("File: {file_decom}".format(file_decom=file_decom), file=sys.stderr)

            # Delete bz2 and decompressed files.
            if delete:
                print("Deleting:\n{file_bz2}\n{file_decom}".format(file_bz2=file_bz2, file_decom=file_decom))
                os.remove(file_bz2)
                os.remove(file_decom)

    return None

if __name__ == '__main__':
    
    file_in_default = "bz2_url_list.txt"
    tmp_dir_default = "/tmp"
    tag_default = "data:big"
    
    parser = argparse.ArgumentParser(description="Download bz2 files from list then upload to Disco and tag.")
    parser.add_argument("--file_in",
                        default=file_in_default, 
                        help=("Input file list of URLs to bz2 files for download. "
                              +"Default: {default}".format(default=file_in_default)))
    parser.add_argument("--tmp_dir",
                        default=tmp_dir_default,
                        help=("Path to save bz2 files for extraction and loading. "
                              +"Default: {default}".format(default=tmp_dir_default)))
    parser.add_argument("--tag",
                        default=tag_default,
                        help=("Disco tag for input file. "
                              +"Default: {default}".format(default=tag_default)))
    parser.add_argument("--delete",
                        action="store_true",
                        help="T/F flag to delete files after uploaded to Disco.")
    args = parser.parse_args()

    print(args)

    main(file_in=args.file_in, tmp_dir=args.tmp_dir, tag=args.tag, delete=args.delete)