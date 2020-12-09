# For pilot collaboration on digital preservation storage with Emory.
# Converts AIP from ARCHive into an AIP compatible with Emory.

# To determine: APTrust does not maintain versions. If we submit another AIP with the same ID, just a later version,
# it overwrites the original. Is that desired or do we add version number to the AIP ID?

import bagit
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

# TODO better error handling than printing to the screen. Log and/or move.


def unpack(aip_zip, aip):
    """Unpack the AIP. Unzips and untars, leaving the AIP's bag directory, named aip-id_bag.
    The file size is just part of the zip name, so it is automatically removed by extracting the bag. """

    # Extracts the contents of the zip file, which is a tar file, and deletes the zip.
    # Some AIPs are just tarred and not zipped.
    if aip_zip.endswith(".bz2"):
        subprocess.run(f"7z x {aip_zip}", stdout=subprocess.DEVNULL, shell=True)
        os.remove(aip_zip)

    # Extracts the contents of the tar file, which is the AIP's bag directory, and deletes the tar file.
    # Calculates the name of the tar file by removing the .bz2 extension, if present, to be able to extract.
    aip_tar = aip_zip.replace(".bz2", "")
    subprocess.run(f"7z x {aip_tar}", stdout=subprocess.DEVNULL, shell=True)
    os.remove(aip_tar)

    # Validates the bag in case there was an undetected problem during storage or unpacking.
    validate_bag(aip)


def size_check(aip):
    """Bag must be under 5 TB. Returns True or False"""
    # TODO: want this function to split if it is too large or leave for staff to do?

    # Calculate the size, in bytes, of the bag by adding the size of each file in the bag.
    bag_size = 0
    for root, dirs, files in os.walk(aip):
        for file in files:
            file_path = os.path.join(root, file)
            bag_size += os.path.getsize(file_path)

    # Evaluate if the size is above the 5 TB limit.
    return bag_size < 5000000000000


def character_check(aip):
    """File and directory names must not contain illegal characters and must be a maximum of 255 characters."""
    # TODO log or fix the error. For now, just working on catching them.
    # TODO if make changes, undo and redo the bag.

    # List of special characters that are not permitted.
    # No file or directory name can include newline, carriage return, tab, vertical tab, or ascii bells.
    # TODO not sure if they would be interpreted as Python codes by os.walk() or if need to do ascii codes.
    not_permitted = ["\n", "\r", "\t", "\v", "\a"]

    for root, directories, files in os.walk(aip):

        # No file or directory name can start with a dash or include any of the not permitted characters.
        # Directories excludes the AIP folder, so test both root (to get the AIP folder) and directories.
        if root.startswith("-") or any(char in root for char in not_permitted):
            return False

        for directory in directories:
            if directory.startswith("-") or any(char in directory for char in not_permitted):
                return False

        for file in files:
            if file.startswith("-") or any(char in file for char in not_permitted):
                return False

            # No file or directory name can exceed 255 characters, including extension.
            # TODO: clarify if this means the entire path, like I've calculated, or individual file and directory names.
            path = os.path.join(root, file)
            if len(path) > 255:
                return False

    # If no error was encountered, return True
    return True


def undo_bag(aip):
    """Copied from bag repo. Script for undoing a single bag. Untested with this script."""

    # Change to the directory that is being unbagged.
    os.chdir(aip)

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
    if aip.endswith('_bag'):
        new_name = aip.replace('_bag', '')
        os.replace(aip, new_name)


def make_bag(aip):
    """Creates a bag and renames to add _bag to the folder."""

    # Bags the AIP folder in place. Both md5 and sha256 checksums are generated to guard against tampering.
    bagit.make_bag(aip, checksums=['md5', 'sha256'])

    # Renames the AIP folder to add _bag to the end of the folder name.
    new_aip_name = f'{aip}_bag'
    os.replace(aip, new_aip_name)


def validate_bag(aip):
    """Validates the bag. If it is not valid, prints the error."""

    new_bag = bagit.Bag(aip)
    try:
        new_bag.validate()
        print("bag is valid")
    except bagit.BagValidationError as e:
        print("bag invalid")
        print(e)


def add_bag_metadata(aip):
    """Add required fields to bagit-info.txt and add new file aptrust-info.txt"""

    # Get metadata from the preservation.xml.

    # Namespaces that find() will use when navigating the xml.
    ns = {"dc": "http://purl.org/dc/terms/", "premis": "http://www.loc.gov/premis/v3"}

    # Parse the data from the XML.
    tree = ET.parse(f"{aip}/data/metadata/{aip.replace('_bag', '')}_preservation.xml")
    root = tree.getroot()

    # Get the group id. Value of the first objectIdentifierType is the ARCHive URI.
    # Start at the 28th character to skip the ARCHive part and just get the group code.
    uri = root.find("aip/premis:object/premis:objectIdentifier/premis:objectIdentifierType", ns).text
    group = uri[28:]

    # Get the title and collection id.
    # TODO: not sure how collection id would work if there is more than one relatedObjectIdentifier.
    title = root.find("dc:title", ns).text
    collection = root.find("aip/premis:object/premis:relationship/premis:relatedObjectIdentifier/premis:relatedObjectIdentifierValue", ns).text

    # Add to bagit-info.txt (source, bag count if multiple, internal sender description and identifier, collection id).
    # TODO: confirm that only include Bag-Count if there is more than one.
    bag = bagit.Bag(aip)
    bag.info['Source-Organization'] = "University of Georgia"
    bag.info['Internal-Sender-Description'] = f"UGA unit: {group}"
    bag.info['Internal-Sender-Identifier'] = aip.replace("_bag", "")
    bag.info['Bag-Group-Identifier'] = collection
    bag.save()

    # Make aptrust-info.txt with title, description, access (institution) and storage option (deep archive?).
    with open(f"{aip}/aptrust-info.txt", "w") as new_file:
        new_file.write(f"Title: {title}\n")
        new_file.write("Description: TBD\n")
        new_file.write("Access: Institution\n")
        new_file.write("Storage-Option: Deep Archive\n")

    # Validate the bag in case any of the above alterations invalidate it.
    validate_bag(aip)


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
    if not (item.endswith(".tar.bz2") or item.endswith(".tar")):
        continue

    print("\nProcessing:", item)

    # Calculates the bag name (aip-id_bag) from the .tar.bz2 name for referring to the AIP after it is unpackaged.
    regex = re.match("^(.*_bag).", item)
    aip_bag = regex.group(1)

    # Unpack the zip (if applicable) and tar file, resulting the bag directory.
    unpack(item, aip_bag)

    # Validate against the APTrust size requirement. Stops processing this AIP if it is too big (above 5 TB)
    size_ok = size_check(aip_bag)
    if not size_ok:
        print("This AIP is above the 5TB limit and must be split")
        continue

    # Validates against the APTrust character requirements. Stops processing this AIP if any are invalid.
    # TODO: replace the invalid characters instead? Would need users to agree.
    character_check_ok = character_check(aip_bag)
    if not character_check_ok:
        print("This AIP has invalid characters")
        continue

    # Updates the bag metadata files.
    add_bag_metadata(aip_bag)

    # Validates the bag.
    validate_bag(aip_bag)

    # Tars the bag.
    subprocess.run(f'7z -ttar a "{aip_bag}.tar" "{aips_directory}/{aip_bag}"', stdout=subprocess.DEVNULL, shell=True)
