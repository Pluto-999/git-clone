from collections import defaultdict
import subprocess
from tempfile import NamedTemporaryFile as Temp
from . import data

def compare_trees(*trees): # takes in a variable number of trees which are dictionaries (mapping of file path -> OID)
    entries = defaultdict(lambda: [None] * len(trees)) # every new entry gets a list with [None, None, ...] - length of list is length of given trees

    # for each tree and each (path, oid) key, value pair (i.e. each file) put the file's OID in the correct slot
    for i, tree in enumerate(trees):
        for path, oid in tree.items():
            entries[path][i] = oid

    for path, oids in entries.items():
        yield (path, *oids)


def diff_trees(t_from, t_to):
    output = b""
    
    for path, o_from, o_to in compare_trees(t_from, t_to):
        if o_from != o_to:
            output += diff_blobs(o_from, o_to, path)
    
    return output

# compare the contents of two blobs (files)
def diff_blobs(o_from, o_to, path="blob"):
    # create 2 temporary files to store the blob contents
    with Temp() as f_from, Temp() as f_to:
        # loop twice - 1st iteration looks at: oid=o_from, f=f_from ; 2nd looks at: oid=o_to, f=f_to
        # i.e. pairing the from and to OID's with their temp file we have just created
        for oid, f in ((o_from, f_from), (o_to, f_to)): 
            if oid:
                f.write(data.get_object(oid))
                f.flush()

        # call the diff command to display the differences between the two files
        with subprocess.Popen(
             ['diff', '--unified', '--show-c-function',
              '--label', f'a/{path}', f_from.name,
              '--label', f'b/{path}', f_to.name],
             stdout=subprocess.PIPE) as proc:
             output, _ = proc.communicate()
 
        return output