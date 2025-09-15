import argparse
import os
import sys
import textwrap

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

    
    # using get_oid allows us to either give a ref name or raw OID hash on the CLI
    oid = base.get_oid # reference to the get_oid function stored in "oid"

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
    cat_file_parser.add_argument("object", type=oid) # user must provide an object ID


    # define the "write-tree" subcommand ("git-clone write-tree") - (tree means directory) 
    # this command is similar to hash-object, but instead of storing an individual file, this stores a whole directory
    write_tree_parser = commands.add_parser("write-tree")
    write_tree_parser.set_defaults(func=write_tree)


    # define the "read-tree" subcommand ("git-clone read-tree <tree_oid>")
    # this command is the opposite of write-tree, in that it takes an OID of a tree and extracts it to the working directory
    # i.e. the IOD of the tree gives us a snapshot of the file contents and writes the contents back into the working directory, potentially overriding the current contents
    read_tree_parser = commands.add_parser("read-tree")
    read_tree_parser.set_defaults(func=read_tree)
    read_tree_parser.add_argument("tree", type=oid)


    # define the "commit" subcommand ("git-clone commit -m "<message>"")
    # this command will create a text file stored in the object database with the type of commit that will store:
    # 1. a message describing the commit
    # 2. when the snapshot was created
    # 3. who created the snapshot
    commit_parser = commands.add_parser("commit")
    commit_parser.set_defaults(func=commit)
    commit_parser.add_argument("-m", "--message", required=True)


    # define the "log" subcommand ("git-clone log <oid>") - optional OID 
    # this command will walk the list of all commits and print them - i.e. the entire commit history is returned
    log_parser = commands.add_parser("log")
    log_parser.set_defaults(func=log)
    log_parser.add_argument("oid", type=oid, nargs="?")


    # define the "checkout" subcommand ("git-clone checkout <oid>")
    # this command will be given a commit OID and populate the working directory with the contents of the commit
    # HEAD will also be moved to point to the given commit OID, meaning HEAD can be moved to any commit we wish, allowing for multiple branches of history
    checkout_parser = commands.add_parser("checkout")
    checkout_parser.set_defaults(func=checkout)
    checkout_parser.add_argument("oid", type=oid)


    # define the "tag" subcommand ("git-clone tag <name of commit> <commit OID>") - optional commit OID (defaults to HEAD)
    # this command will associate a name to an OID so we can then use the name rather than the OID
    tag_parser = commands.add_parser("tag")
    tag_parser.set_defaults(func=tag)
    tag_parser.add_argument("name")
    tag_parser.add_argument("oid", type=oid, nargs="?")

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


def commit(args):
    print(base.commit(args.message))


# starting from HEAD (latest commit) OR the given OID, we parse each commit with get_commit and print out its OID and message
def log(args):
    oid = args.oid or data.get_ref("HEAD")
    while oid:
        commit = base.get_commit(oid)

        print(f'commit {oid}\n')
        print(textwrap.indent(commit.message, "    "))
        print("")

        oid = commit.parent


def tag(args):
    oid = args.oid or data.get_ref("HEAD")
    base.create_tag(args.name, oid)

def checkout(args):
    base.checkout(args.oid)