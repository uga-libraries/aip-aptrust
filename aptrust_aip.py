# For pilot collaboration on digital preservation storage with Emory.
# Converts AIP from ARCHive into an AIP compatible with Emory.

# To determine: APTrust does not maintain versions. If we submit another AIP with the same ID, just a later version,
# it overwrites the original. Is that desired or do we add version number to the AIP ID?

import os

# UNPACKAGE THE AIP

# Unzip and untar. Result is a bag.

# Remove the file size from the bag name.

# Validate bag?


# VALIDATE AGAINST APTRUST REQUIREMENTS

# Bag must be under 5 TB. If not, need to spit.

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


# UPDATE THE BAG METADATA
# https://github.com/LibraryOfCongress/bagit-python, in readme see "Update Bag Manifests"

# Make aptrust-info.txt with title, description, access (institution) and storage option (deep archive?)

# Add to bagit-info.txt (source, bag count if multiple, internal sender description and identifier, collection id)


# PACKAGE THE BAG

# Validate the bag

# Tar the bag


