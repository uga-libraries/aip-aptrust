# For pilot collaboration on digital preservation storage with Emory.
# Converts AIP from ARCHive into an AIP compatible with Emory.

# To determine: APTrust does not maintain versions. If we submit another AIP with the same ID, just a later version,
# it overwrites the original. Is that desired or do we add version number to the AIP ID?

import bagit
import csv
import datetime
import os
import platform
import re
import subprocess
import sys
import xml.etree.ElementTree as et

# TODO errors (and all bag validation results) are logged. Also want to move ones that stop processing?
# TODO: test with errors: tar/zip invalid bag, characters, missing/malformed preservation.xml, paths too long
# TODO: test with other AIPs


def log(log_item):
    """Saves information about an error or event to its own line in a text file. It is its own function, even though
    it is very short, because it is used so frequently. """

    with open("conversion_log.txt", "a") as log_file:
        log_file.write(f'{log_item}\n')


def unpack(aip_zip, aip):
    """Unzips and untars the AIP, using different commands for Windows or Mac, and deletes the zip and tar files. The
    result is just the AIP's bag directory, named aip-id_bag. The file size is only part of the zip or tar name,
    so it is not part of the extracted bag. """
    # todo test the mac commands - came from ARCHive user manual

    # Gets the operating system, which determines the command for unzipping and untarring.
    operating_system = platform.system()

    # Extracts the contents of the zip file, which is a tar file, and deletes the zip.
    # Tests if there is a zip file first since some AIPs are just tarred and not zipped.
    if aip_zip.endswith(".bz2"):
        if operating_system == "Windows":
            subprocess.run(f"7z x {aip_zip}", stdout=subprocess.DEVNULL, shell=True)
        else:
            subprocess.run(f"tar xjf {aip_zip}", shell=True)
        os.remove(aip_zip)

    # Extracts the contents of the tar file, which is the AIP's bag directory, and deletes the tar file.
    # Calculates the name of the tar file by removing the .bz2 extension, if present, to be able to extract.
    # All AIPs will be in a tar file.
    aip_tar = aip_zip.replace(".bz2", "")
    aip_tar_path = os.path.join(aips_directory, aip_tar)
    if operating_system == "Windows":
        subprocess.run(f'7z x "{aip_tar_path}"', stdout=subprocess.DEVNULL, shell=True)
    else:
        subprocess.run(f'tar xf "{aip_tar_path}"', shell=True)
    os.remove(aip_tar)

    # Validates the bag in case there was an undetected problem during storage or unpacking.
    validate_bag(aip, "Unpacking")


def size_check(aip):
    """Tests if the bag is smaller than the limit of 5 TB and returns True or False. """

    # Calculate the size, in bytes, of the bag by totalling the size of each file in the bag.
    bag_size = 0
    for root, dirs, files in os.walk(aip):
        for file in files:
            file_path = os.path.join(root, file)
            bag_size += os.path.getsize(file_path)

    # Evaluate if the size is above the 5 TB limit and return the result.
    return bag_size < 5000000000000


def update_characters(aip):
    """Finds impermissible characters in file and directory names and replaces them with underscores. Names must not
    start with a dash or contain any of 5 whitespace characters. """
    # TODO make a replace function? A lot of overlap between file, directory, and root code.

    # List of special characters that are not permitted: newline, carriage return, tab, vertical tab, or ascii bells.
    # TODO not sure if they would be interpreted as Python codes by os.walk() or if need to do ord with ascii codes.
    not_permitted = ["\n", "\r", "\t", "\v", "\a"]

    # Makes a list of tuples with the names changes, so that they can be saved to a document later.
    changed_names = []

    # Iterates through the directory, starting from the bottom, so that as directory names are changed it does not
    # impact paths for directories that have not yet been tested.
    for root, directories, files in os.walk(aip, topdown=False):

        # Update any file name that starts with a dash or contains impermissible characters.
        for file in files:

            # Variable with the original name that can be updated as needed.
            new_name = file

            # If a file's name starts with a dash, makes a new name that replaces the first dash with an underscore
            # by combining an underscore with everything except the first character of the file's name.
            if new_name.startswith("-"):
                new_name = "_" + new_name[1:]

            # If any impermissible characters are present, makes a new name that replaces them with underscores.
            for character in not_permitted:
                if character in new_name:
                    new_name = new_name.replace(character, "_")

            # If a new name was made that is different from the original name, renames the file to that new name.
            if not file == new_name:
                changed_names.append((os.path.join(root, file), os.path.join(root, new_name)))
                os.replace(os.path.join(root, file), os.path.join(root, new_name))

        # Updates any directory name that starts with a dash or contains impermissible characters.
        for directory in directories:

            # Variable with the original name that can be updated as needed.
            new_name = directory

            # If a directory's name starts with a dash, makes a new name that replaces the first dash with an underscore
            # by combining an underscore with everything except the first character of the directory's name.
            if new_name.startswith("-"):
                new_name = "_" + new_name[1:]

            # If any impermissible characters are present, makes a new name that replaces them with underscores.
            for character in not_permitted:
                if character in new_name:
                    new_name = new_name.replace(character, "_")

            # If a new name was made is different from the original name, renames the directory to that new name.
            if not directory == new_name:
                changed_names.append((os.path.join(root, directory), os.path.join(root, new_name)))
                os.replace(os.path.join(root, directory), os.path.join(root, new_name))

    # Update the AIP name if it starts with a dash or contains impermissible characters. Checking the AIP instead of
    # root because everything except the top level folder (AIP) was already updated as part of directories.
    new_aip_name = aip

    # If the AIP's name starts with a dash, makes a new name that replaces the first dash with an underscore by
    # combining an underscore with everything except the first character of the AIP's name.
    if new_aip_name.startswith("-"):
        new_aip_name = "_" + aip[1:]

    # If any impermissible characters are present, makes a new name that replaces them with underscores.
    for character in not_permitted:
        if character in new_aip_name:
            new_aip_name = new_aip_name.replace(character, "_")

    # If a new name was made is different from the original name, renames the AIP to that new name.
    if not aip == new_aip_name:
        changed_names.append((aip, new_aip_name))
        os.replace(os.path.join(aips_directory, aip), os.path.join(aips_directory, new_aip_name))

    # Updates the bag manifests with the new names so it continues to be valid.
    # bagit prints to the terminal that each renamed thing is not in the manifest, but the resulting bag is valid.
    bag = bagit.Bag(new_aip_name)
    bag.save(manifests=True)

    # If any names were changed, saves them to a CSV as a record of actions taken on the AIP. If the AIP name was
    # changed, the file and directory paths in the CSV will have the old name since the AIP name is changed last.
    if len(changed_names) > 0:
        log("Some files and/or directories were renamed to replace impermissible characters. See renaming.csv.")
        with open("renaming.csv", "a", newline='') as result:
            writer = csv.writer(result)
            # Only adds a header if the document is new (empty).
            if os.path.getsize("renaming.csv") == 0:
                writer.writerow(["Original Name", "Updated Name"])
            for name in changed_names:
                writer.writerow([name[0], name[1]])

    # Returns the new_aip_name so the rest of the script can still refer to the bag.
    # In the vast majority of cases, this is still identical to the original AIP name.
    return new_aip_name


def length_check(aip):
    """Tests if the file and directory name lengths are smaller than the limit of 255 characters. Returns True if all
    names are smaller than the limit or False if any names exceed the limit. Also creates a document with any names
    that exceed the limit for staff review. """

    # Makes a list to store tuples with the path and number of characters for any name exceeding the limit.
    too_long = []

    # Checks the length of the AIP (top level folder). If it is too long, adds it and its length to the too long
    # list. Checking the AIP instead of root because everything except the top level folder (AIP) is also included
    # individually in directories, while root starts including multiple folders as os.walk() navigates the directory.
    if len(aip) > 255:
        too_long.append((aip, len(aip)))

    # Checks the length of every directory and file.
    # If any name is too long, adds its full path and its name length to the too long list.
    for root, directories, files in os.walk(aip):
        for directory in directories:
            if len(directory) > 255:
                path = os.path.join(root, directory)
                too_long.append((path, len(directory)))
        for file in files:
            if len(file) > 255:
                path = os.path.join(root, file)
                too_long.append((path, len(file)))

    # If any names were too long, saves everything that was too long to a file for staff review and returns False so the
    # script stops processing this AIP. Otherwise, returns True so the next step can start.
    if len(too_long) > 0:
        with open("character_limit_exceeded.csv", "a", newline='') as result:
            writer = csv.writer(result)
            # Adds a header if the CSV is empty, meaning this is the first AIP with names exceeding the maximum length.
            if os.path.getsize("character_limit_exceeded.csv") == 0:
                writer.writerow(["Path", "Length of Name"])
            for name in too_long:
                writer.writerow([name[0], name[1]])
        return False
    else:
        return True


def validate_bag(aip, step):
    """Validates the bag and logs the result. Logging even if the bag is valid to have a record of the last time the
    bag was valid. Validation errors are both printed to the terminal by bagit and saved to the log. If the bag is
    not valid, raises an error so that the script knows to stop processing this AIP. """

    new_bag = bagit.Bag(aip)

    # If the bag is valid, logs that the bag is valid, including the workflow step.
    try:
        new_bag.validate()
        log(f"{step}: bag is valid.")

    # If the bag is not valid, adds each error as its own line to the log. The bagit error output has a block of text
    # with errors divided by semicolons.
    except bagit.BagValidationError as errors:
        error_list = str(errors).split("; ")
        for error in error_list:
            log(f"\n{error}")

        # Error used for the script to stop processing this AIP.
        raise ValueError


def add_bag_metadata(aip):
    """Adds required fields to bagit-info.txt and adds a new file aptrust-info.txt. The values for the metadata are
    either consistent for all UGA AIPs or extracted from the preservation.xml file included in the AIP. """

    # Gets metadata from the preservation.xml to use for fields in bagit-info.txt and aptrust-info.txt.

    # Namespaces that find() will use when navigating the preservation.xml.
    ns = {"dc": "http://purl.org/dc/terms/", "premis": "http://www.loc.gov/premis/v3"}

    # Parses the data from the preservation.xml.
    tree = et.parse(f"{aip}/data/metadata/{aip.replace('_bag', '')}_preservation.xml")
    root = tree.getroot()

    # Gets the group id from the value of the first objectIdentifierType (the ARCHive URI).
    # Starts at the 28th character to skip the ARCHive part of the URI and just get the group code.
    uri = root.find("aip/premis:object/premis:objectIdentifier/premis:objectIdentifierType", ns).text
    group = uri[28:]

    # Gets the title from the value of the title element.
    title = root.find("dc:title", ns).text

    # Gets the collection id from the value of the relatedObjectIdentifierValue in the aip section.
    # TODO: not sure how collection id would work if there is more than one relatedObjectIdentifier.
    collection = root.find("aip/premis:object/premis:relationship/premis:relatedObjectIdentifier/premis:relatedObjectIdentifierValue", ns).text

    # Adds required fields to bagit-info.txt.
    bag = bagit.Bag(aip)
    bag.info['Source-Organization'] = "University of Georgia"
    bag.info['Internal-Sender-Description'] = f"UGA unit: {group}"
    bag.info['Internal-Sender-Identifier'] = aip.replace("_bag", "")
    bag.info['Bag-Group-Identifier'] = collection
    bag.save()

    # Makes aptrust-info.txt.
    # TODO: need to save the bag again to get this included in the manifests?
    with open(f"{aip}/aptrust-info.txt", "w") as new_file:
        new_file.write(f"Title: {title}\n")
        new_file.write("Description: TBD\n")
        new_file.write("Access: Institution\n")
        new_file.write("Storage-Option: Deep Archive\n")


# Gets the directory from the script argument and makes that the current directory.
# If it is missing or is not a valid directory, prints an error and quits the script.
try:
    aips_directory = sys.argv[1]
    os.chdir(aips_directory)
except (IndexError, FileNotFoundError):
    print("The aips directory is either missing or not a valid directory.")
    print("Script usage: python /path/aptrust_aip.py /path/aips_directory")
    exit()

# Gets each AIP in the AIPs directory and transforms it into an APTrust-compatible AIP.
# Errors from any step and the results of bag validation are recorded in a log.
log(f"Starting conversion of ARCHive AIPs to APTrust-compatible AIPs on {datetime.date.today()}.")
for item in os.listdir():

    # Skip anything that isn't an AIP based on the file extension.
    if not (item.endswith(".tar.bz2") or item.endswith(".tar")):
        continue

    log(f"\nSTARTING PROCESSING ON: {item}")

    # Calculates the bag name (aip-id_bag) from the tar or zip name for referring to the AIP after the bag is extracted.
    regex = re.match("^(.*_bag).", item)
    aip_bag = regex.group(1)

    # Unpack the zip and/or tar file, resulting in the bag directory.
    # Stops processing this AIP if the bag is invalid.
    try:
        unpack(item, aip_bag)
    except ValueError:
        log("The unpacked bag is not valid. Processing stopped.")
        continue

    # Validates the AIP against the APTrust size requirement. Stops processing this AIP if it is too big (above 5 TB).
    size_ok = size_check(aip_bag)
    if not size_ok:
        log("This AIP is above the 5TB limit and must be split. Processing stopped.")
        continue

    # Validates the AIP against the APTrust character length requirements for directories and files.
    # If any are too long (over 255 characters), produces a list for staff review and stops processing this AIP.
    length_ok = length_check(aip_bag)
    if not length_ok:
        log("This AIP has at least one file or directory above the 255 character limit. Processing stopped.")
        continue

    # Updates the bag metadata files to meet APTrust requirements.
    # Do this step prior to renaming impermissible characters so that the path to the preservation.xml is not changed.
    add_bag_metadata(aip_bag)

    # Checks the AIP for impermissible characters and replaces them with underscores. Produces a list of changed
    # names for the AIP's preservation record. Returns the new name for the AIP bag in case it was altered by this
    # function so the script can continue acting on the bag. If UGA naming conventions are followed, it will almost
    # always be the same as aip_bag.
    new_bag_name = update_characters(aip_bag)

    # Validates the bag. Stops processing this AIP if the bag is invalid.
    try:
        validate_bag(new_bag_name, "Ready to tar")
    except ValueError:
        log("The bag after the character check and adding bag metadata is not valid. Processing stopped.")

    # Tars the bag. Windows uses a different command from Mac/Linux operating systems.
    # TODO: test the mac command. Came from general aip perl script.
    # Gets the operating system, which determines the command for unzipping and untarring.
    operating_system = platform.system()
    bag_path = os.path.join(aips_directory, new_bag_name)

    if operating_system == "Windows":
        subprocess.run(f'7z -ttar a "{new_bag_name}.tar" "{bag_path}"', stdout=subprocess.DEVNULL, shell=True)
    else:
        subprocess.run(f'tar cf {new_bag_name}.tar -C {bag_path}', shell=True)

    log("Processing complete.")
