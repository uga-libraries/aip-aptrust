# For pilot collaboration on digital preservation storage with Emory.
# Converts AIP from ARCHive into an AIP compatible with Emory.

# To determine: APTrust does not maintain versions. If we submit another AIP with the same ID, just a later version,
# it overwrites the original. Is that desired or do we add version number to the AIP ID?

# UNPACKAGE THE AIP

# Unzip and untar. Result is a bag.

# Remove the file size from the bag name.

# Validate bag?


# VALIDATE AGAINST APTRUST REQUIREMENTS

# Bag must be under 5 TB. If not, need to spit.

# No file or directory name can start with a dash.

# No file or directory name can include newline, carriage return, tab, vertical tab, or ascii bells.

# No file  or directory name can exceed 255 characters, including extension.

# If anything was changed, update the bag.


# UPDATE THE BAG METADATA
# https://github.com/LibraryOfCongress/bagit-python, in readme see "Update Bag Manifests"

# Make aptrust-info.txt with title, description, access (institution) and storage option (deep archive?)

# Add to bagit-info.txt (source, bag count if multiple, internal sender description and identifier, collection id)


# PACKAGE THE BAG

# Validate the bag

# Tar the bag


