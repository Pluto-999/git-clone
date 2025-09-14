import argparse
import os
import sys

from . import base
from . import data

def main():
    args = parse_args()
    # each subcommand sets a func attribute to the function that should be run,
    # which is then ran below with the parsed arguments
    args.func(args)

def parse_args():
    # create the top level parser ("git-clone")
    parser = argparse.ArgumentParser()

    # create subparser to handle commands (e.g. "git-clone init", "git-clone commit", etc)
    commands = parser.add_subparsers(dest="command")
    commands.required = True

    
    # define the "init" subcommand ("git-clone init") - create new .git-clone directory
    init_parser = commands.add_parser("init")
    init_parser.set_defaults(func=init) # when "init" is used, call init function (prints hello world)

    
    # define the "hash-object" subcommand ("git-clone hash-object <file>") - save object
    # this command will:
    # 1. read the file's contents of the file path provided
    # 2. hash the contents with SHA-1 to create the OID
    # 3. store the raw contents in ".git-clone/objects/{hash}"
    hash_object_parser = commands.add_parser("hash-object")
    hash_object_parser.set_defaults(func=hash_object)
    hash_object_parser.add_argument("file") # user must provide a file path


    # define the "cat-file" subcommand ("git-clone cat-file <oid>")
    # this command is the opposite of hash-object - it will print an object by its OID 
    cat_file_parser = commands.add_parser("cat-file")
    cat_file_parser.set_defaults(func=cat_file)
    cat_file_parser.add_argument("object") # user must provide an object ID


    # define the "write-tree" subcommand ("git-clone write-tree") - (tree means directory) 
    # this command is similar to hash-object, but instead of storing an individual file, this stores a whole directory
    write_tree_parser = commands.add_parser("write-tree")
    write_tree_parser.set_defaults(func=write_tree)


    # define the "read-tree" subcommand ("git-clone read-tree <tree_oid>")
    # this command is the opposite of write-tree, in that it takes an OID of a tree and extracts it to the working directory
    # i.e. the IOD of the tree gives us a snapshot of the file contents and writes the contents back into the working directory, potentially overriding the current contents
    read_tree_parser = commands.add_parser("read-tree")
    read_tree_parser.set_defaults(func=read_tree)
    read_tree_parser.add_argument("tree")


    return parser.parse_args() # captures what the user typed

# "git-clone init" command creates a new empty repository
# repo data is stored locally in a subdirectory called .git (or in this case, .git-clone)
def init(args):
    data.init() 
    print (f'Initialised empty git-clone repository in {os.getcwd()}/{data.GIT_DIR}')


def hash_object(args):
    with open(args.file, "rb") as f: # read the file in binary mode - treat the file as raw bytes rather than text
        print(data.hash_object(f.read())) # hash the file


def cat_file(args):
    sys.stdout.flush()
    sys.stdout.buffer.write(data.get_object(args.object, expected=None)) # get the object from the given id


def write_tree(args):
    print(base.write_tree())


def read_tree(args):
    base.read_tree(args.tree)