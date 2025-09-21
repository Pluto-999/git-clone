import argparse
import os
import sys
import textwrap
import subprocess
from . import base
from . import data
from . import diff

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
    log_parser.add_argument("oid", default="@", type=oid, nargs="?") # default as "@" (HEAD) means we log all commits before HEAD


    # define the "checkout" subcommand ("git-clone checkout <commit>")
    # this command will be given either a branch name, a tag or a raw commit OID 
    # it will populate the working directory with the contents of that commit
    # HEAD will be updated such that:
    #   - if a branch name is given, HEAD becomes a symbolic ref to that branch
    #   - if a tag or OID is given, HEAD is directly set to that OID (non-symbolic, detached HEAD)
    checkout_parser = commands.add_parser("checkout")
    checkout_parser.set_defaults(func=checkout)
    checkout_parser.add_argument("commit")


    # define the "tag" subcommand ("git-clone tag <name of commit> <commit OID>") - optional commit OID (defaults to HEAD)
    # this command will associate a name to an OID so we can then use the name rather than the OID
    tag_parser = commands.add_parser("tag")
    tag_parser.set_defaults(func=tag)
    tag_parser.add_argument("name")
    tag_parser.add_argument("oid", default="@", type=oid, nargs="?")


    # define the "k" subcommand ("git-clone k")
    # this command will be a visualisation tool to draw all refs and all the commits pointed by the refs
    k_parser = commands.add_parser("k")
    k_parser.set_defaults(func=k)


    # define the "branch" subcommand ("git-clone branch <name of branch> <start point of branch>") - optional name (defaults to listing all branches) and optional start point (defaults to HEAD)
    # creating a new branch means creating a new file in the refs/heads directory of the given name which will contain the OID of the commit the branch currently points to
    branch_parser = commands.add_parser("branch")
    branch_parser.set_defaults(func=branch)
    branch_parser.add_argument("name", nargs="?")
    branch_parser.add_argument("start_point", default="@", type=oid, nargs="?")


    # define the "status" subcommand ("git-clone status")
    # this command will print useful informations about the current, working directory
    status_parser = commands.add_parser("status")
    status_parser.set_defaults(func=status)


    # define the "reset" subcommand ("git-clone reset <commit OID>")
    # this command will move HEAD to point at the given commit OID
    reset_parser = commands.add_parser("reset")
    reset_parser.set_defaults(func=reset)
    reset_parser.add_argument("commit", type=oid)


    # define the "show" subcommand ("git-clone show <OID>") - optional OID (defaults to HEAD)
    # this command will print a commit object showing the commit message and the textual diff from the last commit
    show_parser = commands.add_parser("show")
    show_parser.set_defaults(func=show)
    show_parser.add_argument("oid", default="@", type=oid, nargs="?")


    return parser.parse_args() # captures what the user typed

# "git-clone init" command creates a new empty repository
# repo data is stored locally in a subdirectory called .git (or in this case, .git-clone)
def init(args):
    base.init() 
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


def _print_commit(oid, commit, refs=None):
    refs_str = f'({", ".join(refs)})' if refs else ""
    print(f'commit {oid} {refs_str}\n')
    print(textwrap.indent(commit.message, "    "))
    print("")


# starting from the given OID (to start from HEAD, we use default "@"), we parse each commit with get_commit
# we then print out its OID, message and all the refs that point to that commit
def log(args):
    refs = {}
    for refname, ref in data.iter_refs():
        refs.setdefault(ref.value, []).append(refname)
    
    for oid in base.iter_commits_and_parents({args.oid}):
        commit = base.get_commit(oid)

        _print_commit(oid, commit, refs.get(oid))


def checkout(args):
    base.checkout(args.commit)


def tag(args):
    base.create_tag(args.name, args.oid)


def k(args):
    dot = "digraph commits {\n"
    
    oids = set()
    
    # get every ref and collect the OIDs these refs point to into the oids set
    for ref_name, ref in data.iter_refs(deref=False):
        dot += f'"{ref_name}" [shape=note]\n'
        dot += f'"{ref_name}" -> "{ref.value}"\n'
        if not ref.symbolic:
            oids.add(ref.value)

    # traverse all commits reachable from the collected OIDs
    for oid in base.iter_commits_and_parents(oids):
        commit = base.get_commit(oid)
        dot += f'"{oid}" [shape=box style=filled label="{oid[:10]}"]\n'
        if commit.parent:
            dot += f'"{oid}" -> "{commit.parent}"\n'
    
    dot += "}"
    print(dot)

    with subprocess.Popen (
        ["dot", "-Tpng", "-o", "graph.png"],
        stdin=subprocess.PIPE) as proc:
            proc.communicate (dot.encode ())


def branch(args):
    # if we don't give a branch name, we just want to list out all the branches
    if not args.name:
        current = base.get_branch_name()
        for branch in base.iter_branch_names():
            prefix = "*" if branch == current else " "
            print(f'{prefix} {branch}')

    else:
        base.create_branch(args.name, args.start_point)
        print(f'Branch {args.name} created at {args.start_point[:10]}')


def status(args):
    HEAD = base.get_oid("@")
    branch = base.get_branch_name()
    if branch:
        print(f'On branch {branch}')
    else:
        print(f'HEAD detached at {HEAD[:10]}')


def show(args):
    if not args.oid:
        return
    
    commit = base.get_commit(args.oid)
    parent_tree = None
    if commit.parent:
        parent_tree = base.get_commit(commit.parent).tree
    
    _print_commit(args.oid, commit)

    result = diff.diff_trees(
        base.get_tree(parent_tree), base.get_tree(commit.tree)
    )
    
    sys.stdout.flush()
    sys.stdout.buffer.write(result)


def reset(args):
    base.reset(args.commit)