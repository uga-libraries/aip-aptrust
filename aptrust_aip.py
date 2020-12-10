# For pilot collaboration on digital preservation storage with Emory.
# Converts AIP from ARCHive into an AIP compatible with Emory.

# To determine: APTrust does not maintain versions. If we submit another AIP with the same ID, just a later version,
# it overwrites the original. Is that desired or do we add version number to the AIP ID?

import bagit
import datetime
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

# TODO better error handling than printing to the screen. Log and/or move.
# TODO: test by tar/zip an invalid bag.


def log(log_item):
    """Saves information about an error or event to its own line in a text file."""

    with open("conversion_log.txt", "a") as log_file:
        log_file.write(f'{log_item}\n')


def unpack(aip_zip, aip):
    """Unpack the AIP. Unzips and untars, leaving the AIP's bag directory, named aip-id_bag.
    The file size is just part of the zip name, so it is automatically removed by extracting the bag. """
    # todo mac commandline version

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
    # TODO: does this need to raise the ValueError again if not valid?
    validate_bag(aip, "Unpacking")


def size_check(aip):
    """Bag must be under 5 TB. Returns True or False"""

    # Calculate the size, in bytes, of the bag by adding the size of each file in the bag.
    bag_size = 0
    for root, dirs, files in os.walk(aip):
        for file in files:
            file_path = os.path.join(root, file)
            bag_size += os.path.getsize(file_path)

    # Evaluate if the size is above the 5 TB limit.
    return bag_size < 5000000000000


def character_check(aip):
    """File and directory names must not start with a dash or contain any of 5 impermissible character. Replaces them
    with underscores. """
    # TODO log the changes better: make a csv with before/after including full path instead of adding to log.
    # TODO update the bag. Save with manifest? Need to undo/redo?
    # TODO make a replace function? A lot of overlap between file, directory, and root code.

    # List of special characters that are not permitted.
    # No file or directory name can include newline, carriage return, tab, vertical tab, or ascii bells.
    # TODO not sure if they would be interpreted as Python codes by os.walk() or if need to do ord with ascii codes.
    # TODO added space for testing since I cannot figure out how to replicate any of these characters in a name.
    not_permitted = ["\n", "\r", "\t", "\v", "\a", " "]

    # Iterates over the directory many times since changing the name of something causes file paths for other things to be incorrect.
    # POSSIBLE ALTERNATIVE: https://stackoverflow.com/questions/40556685/rename-directorys-recursively-in-python
    # Seemed like combining dash and characters was working, but dash isn't getting replaced now.

    # Update file name if it starts with a dash or contains impermissible characters.
    for root, directories, files in os.walk(aip):
        for file in files:

            # Variable with the original name that can be updated as needed.
            new_name = file

            # If file's name starts with a dash, makes a new name that replaces the dash with an underscore.
            # To replace only the first dash, combine underscore with everything except the first character of file's name.
            if file.startswith("-"):
                new_name = "_" + file[1:]

            # If any impermissible characters are present, makes a new name that replaces them with underscores.
            for character in not_permitted:
                if character in file:
                    new_name = new_name.replace(character, "_")

            # If a new name was made is different from the original name, renames root to that new name.
            if not file == new_name:
                log(f"Changed {file} to {new_name}.")
                os.replace(os.path.join(root, file), os.path.join(root, new_name))

    # Update directory name if it starts with a dash or contains impermissible characters.
    for root, directories, files in os.walk(aip, topdown=False):
        for directory in directories:

            # Variable with the original name that can be updated as needed.
            new_name = directory

            # If directory's name starts with a dash, makes a new name that replaces the dash with an underscore.
            # To replace only the first dash, combine underscore with everything except the first character of directory's name.
            if directory.startswith("-"):
                new_name = "_" + directory[1:]

            # If any impermissible characters are present, makes a new name that replaces them with underscores.
            for character in not_permitted:
                if character in directory:
                    new_name = new_name.replace(character, "_")

            # If a new name was made is different from the original name, renames root to that new name.
            if not directory == new_name:
                log(f"Changed {directory} to {new_name}.")
                os.replace(os.path.join(root, directory), os.path.join(root, new_name))

    # Update root name if it starts with a dash or contains impermissible characters.
    for root, directories, files in os.walk(aip):

        # Variable with the original name that can be updated as needed.
        new_name = root

        # If root's name starts with a dash, makes a new name that replaces the dash with an underscore.
        # To replace only the first dash, combine underscore with everything except the first character of root's name.
        if root.startswith("-"):
            new_name = "_" + root[1:]

        # If any impermissible characters are present, makes a new name that replaces them with underscores.
        for character in not_permitted:
            if character in root:
                new_name = new_name.replace(character, "_")

        # If a new name was made is different from the original name, renames root to that new name.
        if not root == new_name:
            log(f"Changed {root} to {new_name}.")
            os.replace(root, new_name)


def length_check(aip):
    """File and directory names must be a maximum of 255 characters."""
    # TODO: this was tested as part of character_check but not on its own.
    # TODO: this function isn't called yet.
    # TODO: create a document of all the ones that are too long for staff to edit?
    # TODO: really hopping the 255 is for individual folders and file names, not for the entire path.

    # Iterates through all levels of the AIP directory.
    for root, directories, files in os.walk(aip):
        # Iterates through every file at this level of the of AIP directory.
        for file in files:
            # Recreates the entire file path.
            path = os.path.join(root, file)
            # Evaluates if the path is longer than permitted.
            if len(path) > 255:
                log(f"{path} has {len(path)} characters, which exceeds the 255 character limit. Processing stopped.")
                return False


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


def validate_bag(aip, step):
    """Validates the bag and logs the result. Record if valid or not for a record of the last time the bag was valid.
    Validation errors do print to the terminal but they are also saved to the log. If the bag is not valid,
    raises an error so that the script knows to stop processing this AIP. """

    new_bag = bagit.Bag(aip)
    try:
        new_bag.validate()
        log(f"{step}: bag is valid.")

    except bagit.BagValidationError as errors:
        # Splits each error from the block of text so each error is saved on its own line in the log.
        error_list = str(errors).split("; ")
        for error in error_list:
            log(f"\n{error}")

        # Error used for the script to stop processing this AIP.
        raise ValueError


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
    bag = bagit.Bag(aip)
    bag.info['Source-Organization'] = "University of Georgia"
    bag.info['Internal-Sender-Description'] = f"UGA unit: {group}"
    bag.info['Internal-Sender-Identifier'] = aip.replace("_bag", "")
    bag.info['Bag-Group-Identifier'] = collection
    bag.save()

    # Make aptrust-info.txt with title, description, access (institution) and storage option (deep archive?).
    # TODO: need to save the bag again to get this included in the manifests?
    with open(f"{aip}/aptrust-info.txt", "w") as new_file:
        new_file.write(f"Title: {title}\n")
        new_file.write("Description: TBD\n")
        new_file.write("Access: Institution\n")
        new_file.write("Storage-Option: Deep Archive\n")


# Get directory from script argument and make that the current directory.
try:
    aips_directory = sys.argv[1]
    os.chdir(aips_directory)
except (IndexError, FileNotFoundError):
    print("The aips directory is either missing or not a valid directory.")
    print("Script usage: python /path/aptrust_aip.py /path/aips_directory")
    exit()

# Get each AIP and transform it into an APTrust-compatible AIP.
# Results of each step are recorded in a log.
log(f"Starting conversion of ARCHive AIPs to APTrust-compatible AIPs on {datetime.date.today()}.")
for item in os.listdir():

    # Skip anything that isn't an AIP.
    if not (item.endswith(".tar.bz2") or item.endswith(".tar")):
        continue

    log(f"\nSTARTING PROCESSING ON: {item}")

    # Calculates the bag name (aip-id_bag) from the .tar.bz2 name for referring to the AIP after it is unpacked.
    regex = re.match("^(.*_bag).", item)
    aip_bag = regex.group(1)

    # Unpack the zip (if applicable) and tar file, resulting in the bag directory.
    # Stops processing this AIP if the bag is invalid.
    try:
        unpack(item, aip_bag)
    except ValueError:
        log("The unpacked bag is not valid. Processing stopped.")
        continue

    # Validate against the APTrust size requirement. Stops processing this AIP if it is too big (above 5 TB)
    size_ok = size_check(aip_bag)
    if not size_ok:
        log("This AIP is above the 5TB limit and must be split. Processing stopped.")
        continue

    # Validates against the APTrust character requirements. Replaces impermissible characters with underscores.
    character_check(aip_bag)

    # Updates the bag metadata files.
    add_bag_metadata(aip_bag)

    # Validates the bag.
    # Stops processing this AIP if the bag is invalid.
    try:
        validate_bag(aip_bag, "Ready to tar")
    except ValueError:
        log("The bag after the character check and adding bag metadata is not valid. Processing stopped.")

    # Tars the bag.
    # TODO: mac command line tar/zip
    subprocess.run(f'7z -ttar a "{aip_bag}.tar" "{aips_directory}/{aip_bag}"', stdout=subprocess.DEVNULL, shell=True)

    log("Processing complete.")
