import os
from . import data
import itertools
import operator
from collections import namedtuple
import string

## this module has the basic higher-level logic of git-clone using the object database implemented in data.py


# creates a tree object that records the names of entries, their types and the object ID's of these entries
def write_tree(directory="."):
    entries = []
    with os.scandir(directory) as it: # iterate through everything in the given directory (either a file or another directory)
        for entry in it:
            full = f'{directory}/{entry.name}'
            if is_ignored(full):
                continue
            
            # if we see a file in the given directory, we mark its type as "blob" and store its contents in the object database (with hash_object)
            if entry.is_file(follow_symlinks=False):
                type_ = "blob"
                with open(full, "rb") as f:
                    oid = data.hash_object(f.read())
            
            # if we see a directory, we mark its type as "tree" and recurse into that directory by calling write_tree again
            elif entry.is_dir(follow_symlinks=False):
                type_ = "tree"
                oid = write_tree(full)
            
            entries.append((entry.name, oid, type_))


    # building the tree object string
    tree = "".join(f'{type_} {oid} {name}\n'
        for name, oid, type_ in sorted(entries)
    )

    # store the tree string as a new tree object with type "tree" in .git-clone/objects
    return data.hash_object(tree.encode(), "tree")
    

# takes an OID of a tree object, loads it from the object database and yields the raw string values of each entry
def _iter_tree_entries(oid):
    if not oid: 
        return 

    tree = data.get_object(oid, "tree")
    
    for entry in tree.decode().splitlines():
        type_, oid, name = entry.split(" ", 2)
        yield type_, oid, name

# recursively parse a given tree into a dictonary - returns a dictionary mapping: file paths -> blob object IDs
def get_tree(oid, base_path=""):
    result = {}
    
    for type_, oid, name in _iter_tree_entries(oid):
        assert "/" not in name
        assert name not in ("..", ".")
        path = base_path + name
        if type_ == "blob":
            result[path] = oid
        elif type_ == "tree":
            result.update(get_tree(oid, f'{path}/'))
        else:
            assert False, f'Unknown tree entry {type_}'

    return result

# uses get_tree to get the file OIDs and writes them into the working directory
def read_tree(tree_oid):
    _empty_current_directory()
    for path, oid in get_tree(tree_oid, base_path="./").items():
        os.makedirs(os.path.dirname(path), exist_ok=True) # ensures the directory structure exists before writing to the file
        # write the contents of the object into the working directory file
        with open(path, "wb") as f:
            f.write(data.get_object(oid))

# we want to delete all existing stuff in the working directory before reading so we don't have any old files left around after a "read-tree" command
# e.g. without this, if we saved tree A with a.txt then saved tree B with a.txt and b.txt and then do "read-tree" A, we would have b.txt left over in the working directory
def _empty_current_directory():
    for root, dirnames, filenames in os.walk(".", topdown=False):
        
        # remove all files 
        for filename in filenames:
            path = os.path.relpath(f'{root}/{filename}')
            if is_ignored(path) or not os.path.isfile(path):
                continue
            os.remove(path)
        
        # remove all directories
        for dirname in dirnames:
            path = os.path.relpath(f'{root}/{dirname}')
            if is_ignored(path):
                continue
            try:
                os.rmdir(path)
            except (FileNotFoundError, OSError):
                pass


# takes a messsage for the commit, then calls write_tree() for a snapshot of the current working directory, and builds a commit object (text file in object database)
def commit(message):
    commit = f'tree {write_tree()}\n'
    
    # here we use the HEAD to link this new commit being created to the previous commit (called "parent commit")
    # the previous commit OID is saved in the "parent" key on the commit object
    # this means we can retrieve the entire list of commits just by referencing the last commit, 
    # as we can start from the HEAD, read the "parent" key on the HEAD commit to get the previous commit and so on - like a linked list
    HEAD = data.get_ref("HEAD")
    if HEAD:
        commit += f'parent {HEAD}\n'

    commit += '\n'
    commit += f'{message}\n'

    oid = data.hash_object(commit.encode(), "commit")

    # update the head to set it to the OID of this current, new commit so that it can be used as the parent for the next commit
    data.update_ref("HEAD", oid)

    return oid


Commit = namedtuple("Commit", ["tree", "parent", "message"])

def get_commit(oid):
    parent = None

    # load the commit object from the object database and split it into lines
    commit = data.get_object(oid, "commit").decode()
    lines = iter(commit.splitlines())

    for line in itertools.takewhile(operator.truth, lines):
        key, value = line.split(" ", 1)
        # get the tree OID
        if key == "tree":
            tree = value
        # get the parent commit OID
        elif key == "parent":
            parent = value
        else:
            assert False, f'Unkown field {key}'

    message = '\n'.join(lines)
    return Commit(tree, parent, message)


def checkout(oid):
    commit = get_commit(oid) # get the commit referenced by the given OID
    read_tree(commit.tree) # load the files of that commit into the current working directory
    data.update_ref("HEAD", oid) # set the HEAD to now point to the commit OID we are checking out


# calls update_ref which will write the given OID into the file named with the given tag
# e.g. if we do: git-clone tag test, we create refs/tags/test which will store the OID
def create_tag(name, oid):
    data.update_ref(f'refs/tags/{name}', oid)


# resolves a given name to an OID - name can be either a ref (so returns the OID the ref stores) or an OID (so returns the same OID)
def get_oid(name):
    refs_to_try = [
        f'{name}', # root directory (.git-clone), meaning we can specify: "refs/tags/mytag"
        f'refs/{name}', # .git-clone/refs, meaning we can specify: "tags/mytag"
        f'refs/tags/{name}', # .git-clone/refs/tags, meaning we can specify: "mytag" 
        f'refs/heads/{name}' # .git-clone/refs/heads - for a future change
    ]

    for ref in refs_to_try:
        if data.get_ref(ref):
            return data.get_ref(ref)
        
    # checkout with the raw hash OID - if the string is exactly 40 characters long and all characters are hex digits
    is_hex = all(c in string.hexdigits for c in name)
    if len(name) == 40 and is_hex:
        return name
    
    assert False, f'Unknown name {name}'


def is_ignored(path):
    return ".git-clone" in path.split("/")