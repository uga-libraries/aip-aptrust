# For pilot collaboration on digital preservation storage with Emory.
# Converts AIP from ARCHive into an AIP compatible with Emory.

# To determine: APTrust does not maintain versions. If we submit another AIP with the same ID, just a later version,
# it overwrites the original. Is that desired or do we add version number to the AIP ID?

import bagit
import os
import re
import subprocess
import sys


def unpackage(aip):
    """Unpackage the AIP that is stored in ARCHive. Unzips, untars, removes size from the bag directory name.
    The result is still a bag."""
    # TODO could validate the bag at this stage in case there was an undetected problem during storage.

    # Extracts the contents of the zip file, which is a tar file.
    subprocess.run(f"7z x {aip}", stdout=subprocess.DEVNULL, shell=True)

    # Extracts the contents of the tar file, which is the AIP's bag directory.

    # Deletes the .tar.bz2 and .tar files.

    # Remove the file size from the bag directory name. os.replace()

# Validate bag? validate_bag()


# VALIDATE AGAINST APTRUST REQUIREMENTS

# Bag must be under 5 TB. If not, need to spit.
# Getting the size of a file: os.path.getsize(FILEPATH)

# File and directory names must not contain illegal characters and must be a maximum of 255 characters.
def validate_names(aip):
    """Outline for a function that will be needed."""

    for root, directories, files in os.walk(aip):
        pass

        # No file or directory name can start with a dash.

        # No file or directory name can include newline, carriage return, tab, vertical tab, or ascii bells.

        # No file or directory name can exceed 255 characters, including extension.


# If anything was changed, undo and redo the bag.
def undo_bag(bag):
    """Copied from bag repo. Script for undoing a single bag. Untested with this script."""

    # Change to the directory that is being unbagged.
    os.chdir(bag)

    # Delete the bag metadata files, which are all text files.
    for doc in os.listdir('.'):
        if doc.endswith('.txt'):
            os.remove(doc)

    # Move the contents from the data folder into the parent directory.
    for item in os.listdir('data'):
        os.replace(f'data/{item}', item)

    # Delete the now-empty data folder.
    os.rmdir('data')

    # Delete '_bag' from the end of the directory name if the standard bag naming convention was used.
    if bag.endswith('_bag'):
        new_name = bag.replace('_bag', '')
        os.replace(bag, new_name)


def make_bag(aip_id):
    """Creates a bag and renames to add _bag to the folder."""

    # Bags the AIP folder in place. Both md5 and sha256 checksums are generated to guard against tampering.
    bagit.make_bag(aip_id, checksums=['md5', 'sha256'])

    # Renames the AIP folder to add _bag to the end of the folder name.
    new_aip_name = f'{aip_id}_bag'
    os.replace(aip_id, new_aip_name)


def validate_bag(aip):
    """Validates the bag. If it is not valid, prints the error."""

    new_bag = bagit.Bag(aip)
    try:
        new_bag.validate()
        print("bag is valid")
    except bagit.BagValidationError as e:
        print("bag invalid")
        print(e)


# UPDATE THE BAG METADATA
# https://github.com/LibraryOfCongress/bagit-python, in readme see "Update Bag Manifests"

# Make aptrust-info.txt with title, description, access (institution) and storage option (deep archive?)

# Add to bagit-info.txt (source, bag count if multiple, internal sender description and identifier, collection id)


# PACKAGE THE BAG

# Validate the bag:validate_bag()

# Tar the bag
# aip = "todo"
# subprocess.run(f'7z -ttar a "{aip}.tar" "{aips_directory}/{aip}"', stdout=subprocess.DEVNULL, shell=True)

# Get directory from script argument and make that the current directory.
try:
    aips_directory = sys.argv[1]
    os.chdir(aips_directory)
except (IndexError, FileNotFoundError):
    print("The aips directory is either missing or not a valid directory.")
    print("Script usage: python /path/aptrust_aip.py /path/aips_directory")
    exit()

# Get each AIP and transform it into an APTrust-compatible AIP.
for item in os.listdir():

    # Skip anything that isn't an AIP
    # TODO: BMAC can sometimes be just tar or just zip; check the documentation.
    if not item.endswith(".tar.bz2"):
        continue

    print("Processing:", item)

    # Calculates the AIP ID from the .tar.bz2 name for referring to the AIP after it is unpackaged.
    # TODO: once see how the script uses this, may decide to leave _bag as part of it.
    regex = re.match("^(.*)_bag", item)
    aip_id = regex.group(1)
    print(aip_id)

    # Unpackage the tar and zip, and remove the size from the bag directory name.
    # TODO: handle BMAC that don't have both.
    unpackage(item)

