import os
import hashlib
from collections import namedtuple

GIT_DIR = ".git-clone"


# creating a wrapper that gives every ref file a structured meaning
# a direct ref (e.g. RefValue(symbolic=False, value=784...)) stores a commit OID string (the "value") directly in the ref file
# a symbolic ref points to another ref, and not a raw OID string (e.g. RefValue(symbolic=True, value="refs/heads/main"))
RefValue = namedtuple("RefValue", ["symbolic", "value"])


def init():
    os.makedirs(GIT_DIR, exist_ok=True) # create the ".git-clone" directory for the "init" command
    os.makedirs(f'{GIT_DIR}/objects', exist_ok=True)


# each object will have a type tag, the default being "blob" since by default an object is just a collection of bytes with no further semantic meaning
def hash_object(data, type_="blob"):
    obj = type_.encode() + b'\x00' + data # prefix the file data with the type (which is converted into a sequence of bytes with encode()) before hashing and storing
    oid = hashlib.sha1(obj).hexdigest() # object id is the filename which is the SHA-1 hash of the given data (content-addressable)
    # store the raw data in ".git-clone/objects/<oid>"
    with open(f'{GIT_DIR}/objects/{oid}', "wb") as out:
        out.write(obj)
    return oid # return the object id to be printed in cli.py


def get_object(oid, expected="blob"):
    with open(f'{GIT_DIR}/objects/{oid}', "rb") as f:
        obj = f.read()

    type_, _, content = obj.partition(b'\x00')
    type_ = type_.decode()

    if expected is not None: # we can pass expected=None if we don't want to verify the type - useful for cat-file which is a debug for printing all objects
        assert type_ == expected, f'Expected {expected}, got {type_}'

    return content


# NOTE: deref=True means follow symbolic refs until we reach the final OID, while deref=False means stop at the first ref we encounter, even if it's symbolic
# e.g.
# HEAD → "ref: refs/heads/main"
# refs/heads/main → "784eedd9..."
# with deref=True, we get RefValue(symbolic=False, value="784eedd9...")
# with deref=False, we get RefValue(symbolic=True, value="refs/heads/main")


# writes an ref to disk
# a ref can point directly to an OID (direct ref) or to another ref (symbolic ref)
# e.g. .git-clone/refs/tags/testTag → "784e..." (direct ref: commit OID)
# e.g. .git-clone/HEAD → "ref: ref/heads/main" (symbolic ref: points to branch)
def update_ref(ref, value, deref=True):
    ref = _get_ref_internal(ref, deref)[0]

    assert value.value
    if value.symbolic:
        value = f'ref: {value.value}'
    else:
        value = value.value

    ref_path = f'{GIT_DIR}/{ref}'
    os.makedirs(os.path.dirname(ref_path), exist_ok=True)
    with open(ref_path, "w") as f:
        f.write(value)


# reads the value of a ref file (e.g. HEAD, refs/tags/<tag>, refs/heads/<branch>)
def get_ref(ref, deref=True):
    return _get_ref_internal(ref, deref)[1]
        

# helper function that resolves a ref to its final direct target
# - If given a direct ref (file contains an OID), it returns (ref_name, RefValue(symbolic=False, value=<OID>))
# - If given a symbolic ref (file contains "ref: <other_ref>"), it recursively follows the chain
#   until it reaches a direct ref, and returns the final ref name and its OID
def _get_ref_internal(ref, deref):
    ref_path = f'{GIT_DIR}/{ref}'
    value = None

    if os.path.isfile(ref_path):
        with open(ref_path) as f:
            value =  f.read().strip()

    # if the ref is a symbolic ref, this means it points to another ref instead of a commit OID directly
    # therefore recursively resolve until we reach an OID
    symbolic = bool (value) and value.startswith("ref:")
    if symbolic:
        value = value.split(":", 1)[1].strip()
        if deref:
            return _get_ref_internal(value, deref=True)
    
    return ref, RefValue(symbolic=symbolic, value=value)


# a generator function that will iterate on all available refs
# it will return HEAD from the git-clone root directory and everything under .git-clone/refs
def iter_refs(deref=True):
    refs = ["HEAD"]
    for root, _, filenames in os.walk(f'{GIT_DIR}/refs/'):
        root = os.path.relpath(root, GIT_DIR) # make the root path relative to GIT_DIR so we don't get absolute paths
        refs.extend(f'{root}/{name}' for name in filenames)

    for ref_name in refs:
        yield ref_name, get_ref(ref_name, deref=deref)