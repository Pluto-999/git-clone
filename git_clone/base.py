import os
from . import data

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

# recursively parse a given tree into a dictonary - returns a dictionary mapping file paths -> blob object IDs
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

def is_ignored(path):
    return ".git-clone" in path.split("/")