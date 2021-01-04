# For pilot collaboration on digital preservation storage with Emory.
# Batch converts AIPs from ARCHive into AIPs compatible with APTrust.
# Prior to running this script, export the AIPs from ARCHive and save to a folder (aips directory)
# Script usage: python /path/aptrust_aip.py /path/aips_directory

"""
Questions for users:
    * APTrust overwrites old AIPs with a new version. Do we want all versions or just most recent in APTrust?
    * Changes to the log structure (csv?) or content (more or less info)?
    * Save the name change log to the AIP metadata folder?
    * Use of fields, especially description, in bagit-info.txt and aptrust-info.txt?
    * Ok with replacing those characters with underscores? Unlikely to come up unless someone starts an AIP with dash
    * Want to delete the bag and just have the final tar files or helpful to have unpacked for review?
    * AIP size check is slow - even 5 GB was a noticeable lag. Want to be able to turn that off?
"""

# todo: the results have not been tested with APTrust ingest

import bagit
import csv
import datetime
import os
import platform
import re
import subprocess
import sys
import xml.etree.ElementTree as et


def log(log_item):
    """Saves information about an error or event to its own line in a text file. It is its own function, even though
    it is very short, because it is used so frequently. """

    with open("conversion_log.txt", "a") as log_file:
        log_file.write(f'{log_item}\n')


def move_error(error_name, aip):
    """Moves the AIP folder to an error folder, named with the error type, so it is clear what step the AIP stopped on.
    Makes the error folder if it does not already exist prior to moving the AIP folder. """

    if not os.path.exists(f"errors/{error_name}"):
        os.makedirs(f"errors/{error_name}")
    os.replace(aip, f"errors/{error_name}/{aip}")


def unpack(aip_zip, aip):
    """Unzips (if applicable) and untars the AIP, using different commands for Windows or Mac, and deletes the zip
    and tar files. The result is just the AIP's bag directory, named aip-id_bag. The file size is only part of the
    zip or tar name, so it is not part of the extracted bag. """
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

    # Validates the bag in case there was a problem during storage or unpacking.
    # TODO: is it more clear to make this part of the main body of the script instead of being in this function?
    validate_bag(aip, "Unpacking")


def size_check(aip):
    """Tests if the bag is smaller than the limit of 5 TB and returns True or False. """

    # Calculate the size, in bytes, of the bag by totalling the size of each file in the bag.
    # TODO: how does this compare to the payload-oxum size in bag-info.txt?
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

    def rename(original, join_root=True):
        """Renames the original file or directory by replacing any starting dashes or impermissible characters with
        an underscore. If the name is changed, it is added to the changed_names list. The new name, which may be the
        same as the original, is returned. The new name is only saved and used when the original name supplied is an
        AIP name so the script can continue to refer to the bag even if the name changes. """

        # Variable with the original name that can be updated as needed.
        new_name = original

        # If the name starts with a dash, updates the new name to replace the first dash with an underscore by
        # combining an underscore with everything except the first character of the name.
        if new_name.startswith("-"):
            new_name = "_" + new_name[1:]

        # If any impermissible characters are present in the new name, replaces them with underscores.
        for character in not_permitted:
            if character in new_name:
                new_name = new_name.replace(character, "_")

        # If the new name is different from the original name, renames the file or directory to the new name.
        # The default is to include the root as part of the path, but this is not done for AIPs (AIP is the root).
        # Also saves the original and new name to a list of changed names to use for making a record of the change.
        # TODO: is it safer to return the tuple instead of updating a variable from outside this function?
        if not original == new_name:
            if join_root:
                changed_names.append((os.path.join(root, original), os.path.join(root, new_name)))
                os.replace(os.path.join(root, original), os.path.join(root, new_name))
            else:
                changed_names.append((original, new_name))
                os.replace(original, new_name)

        # This is needed for AIPs only, so the script can continue to refer to the bag.
        return new_name

    # List of special characters that are not permitted: newline, carriage return, tab, vertical tab, and ascii bells.
    # Note: Could not test in file or directory names since none are permitted by a modern OS. Tested within text files.
    not_permitted = ["\n", "\r", "\t", "\v", "\a"]

    # Makes a list of tuples with the original and updated name so that they can be saved to a CSV later.
    changed_names = []

    # Iterates through the directory, starting from the bottom, so that as directory names are changed it does not
    # impact paths for directories that have not yet been tested.
    for root, directories, files in os.walk(aip, topdown=False):

        # Updates any file name that starts with a dash or contains impermissible characters.
        for file in files:
            rename(file)

        # Updates any directory name that starts with a dash or contains impermissible characters.
        for directory in directories:
            rename(directory)

    # Updates the AIP name if it starts with a dash or contains impermissible characters. Checking the AIP instead of
    # root because everything in root except the top level folder (AIP) was already updated as part of directories.
    new_aip_name = rename(aip, join_root=False)

    # Updates the bag manifests with the new names so it continues to be valid.
    # Note: bagit prints to the terminal that each renamed thing is not in the manifest, but the resulting bag is valid.
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

    # Checks the length of the AIP (top level folder). If it is too long, adds it and its length to the too_long
    # list. Checking the AIP instead of root because everything in root except the top level folder (AIP) is also
    # included individually in directories.
    if len(aip) > 255:
        too_long.append((aip, len(aip)))

    # Checks the length of every directory and file.
    # If any name is too long, adds its full path and its name length to the too_long list.
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
    """Validates the bag and logs the result. Logs even if the bag is valid to have a record of the last time the
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
    """Adds additional fields to bagit-info.txt and adds a new file aptrust-info.txt. The values for the metadata
    fields are either consistent for all UGA AIPs or are extracted from the preservation.xml file included in the
    AIP. """
    # TODO: since this is called within a try/except, does it need try/except as part of the function? Or will it raise
    #  the error and stop the function fine on its own?

    # Gets metadata from the preservation.xml to use for fields in bagit-info.txt and aptrust-info.txt.

    # Namespaces that find() will use when navigating the preservation.xml.
    ns = {"dc": "http://purl.org/dc/terms/", "premis": "http://www.loc.gov/premis/v3"}

    # Parses the data from the preservation.xml.
    # If the preservation.xml is not found, raises an error so the script can stop processing this AIP.
    try:
        tree = et.parse(f"{aip}/data/metadata/{aip.replace('_bag', '')}_preservation.xml")
        root = tree.getroot()
    except FileNotFoundError:
        raise FileNotFoundError

    # Gets the group id from the value of the first objectIdentifierType (the ARCHive URI).
    # Starts at the 28th character to skip the ARCHive part of the URI and just get the group code.
    # If this field (which is required) is missing, raises an error so the script can stop processing this AIP.
    # ParseError means the field is not found (object_id_field = None), AttributeError is from uri = None.text.
    try:
        object_id_field = root.find("aip/premis:object/premis:objectIdentifier/premis:objectIdentifierType", ns)
        uri = object_id_field.text
        group = uri[28:]
    except (et.ParseError, AttributeError):
        raise ValueError("premis:objectIdentifierType")

    # Gets the title from the value of the title element.
    # If this field (which is required) is missing, raises an error so the script can stop processing this AIP.
    # ParseError means the field is not found (title_field = None), AttributeError is from tile = None.text.
    try:
        title_field = root.find("dc:title", ns)
        title = title_field.text
    except (et.ParseError, AttributeError):
        raise ValueError("dc:title")

    # Gets the collection id from the value of the first relatedObjectIdentifierValue in the aip section.
    # If there is no collection id (e.g. for some web archives), supplies default text.
    # ParseError means the field is not found (relationship_id_field = None), AttributeError is from collection = None.text.
    try:
        relationship_id_field = root.find("aip/premis:object/premis:relationship/premis:relatedObjectIdentifier/premis:relatedObjectIdentifierValue", ns)
        collection = relationship_id_field.text
    except (et.ParseError, AttributeError):
        collection = "This AIP is not part of a collection."

    # For DLG newspapers, the first relationship is dlg and the second is the collection.
    # Updates the value of collection to be the text of the second relationship instead.
    if collection == "dlg":
        collection = root.find("aip/premis:object/premis:relationship[2]/premis:relatedObjectIdentifier/premis:relatedObjectIdentifierValue", ns).text

    # Adds required fields to bagit-info.txt.
    # todo confirm values with staff
    bag = bagit.Bag(aip)
    bag.info['Source-Organization'] = "University of Georgia"
    bag.info['Internal-Sender-Description'] = f"UGA unit: {group}"
    bag.info['Internal-Sender-Identifier'] = aip.replace("_bag", "")
    bag.info['Bag-Group-Identifier'] = collection

    # Makes aptrust-info.txt.
    # todo: confirm values with staff
    with open(f"{aip}/aptrust-info.txt", "w") as new_file:
        new_file.write(f"Title: {title}\n")
        new_file.write("Description: TBD\n")
        new_file.write("Access: Institution\n")
        new_file.write("Storage-Option: Deep Archive\n")

    # Saves the bag to update the tag manifests to add aptrust-info.txt and update the checksums for bagit-info.txt.
    # If successfully saves, adds note to log to document changes to the bag.
    # TODO: should this be in a try/except or ok with it crashing if bag can't save? Don't know what the error is.
    bag.save(manifests=True)
    log("bagit-info.txt was successfully updated.")
    log("aptrust-info.txt was successfully added to the bag.")


def tar_bag(aip):
    """Tars the bag, using the appropriate command for Windows (7zip) or Mac/Linux (tar) operating systems."""
    # todo: test the mac command. Came from general aip perl script.

    # Gets the operating system, which determines the command for unzipping and untarring.
    operating_system = platform.system()

    bag_path = os.path.join(aips_directory, aip)

    # Tars the AIP using the operating system-specific command.
    if operating_system == "Windows":
        subprocess.run(f'7z -ttar a "{aip}.tar" "{bag_path}"', stdout=subprocess.DEVNULL, shell=True)
    else:
        subprocess.run(f'tar cf {aip}.tar -C "{bag_path}"', shell=True)


# Gets the directory from the script argument and makes that the current directory.
# If it is missing or is not a valid directory, prints an error and quits the script.
try:
    aips_directory = sys.argv[1]
    os.chdir(aips_directory)
except (IndexError, FileNotFoundError, NotADirectoryError):
    print("The aips directory is either missing or not a valid directory.")
    print("Script usage: python /path/aptrust_aip.py /path/aips_directory")
    exit()

# Tracks the number of AIPs either fully converted or that encountered errors for including as a summary of the
# script's success in the log.
aips_converted = 0
aips_errors = 0

# Gets each AIP in the AIPs directory and transforms it into an APTrust-compatible AIP.
# Anticipated errors from any step and the results of bag validation are recorded in a log.
# Any AIP with an anticipated error is moved to a folder with the error name so processing can stop on that AIP.
log(f"Starting conversion of ARCHive AIPs to APTrust-compatible AIPs at {datetime.datetime.today()}.")
for item in os.listdir():

    # Skip anything that isn't an AIP based on the file extension.
    if not (item.endswith(".tar.bz2") or item.endswith(".tar")):
        continue

    log(f"\nSTARTING PROCESSING ON: {item}")

    # Calculates the bag name (aip-id_bag) from the tar or zip name for referring to the AIP after the bag is extracted.
    # Stops processing this AIP if the bag name does not match the expected pattern.
    try:
        regex = re.match("^(.*_bag).", item)
        aip_bag = regex.group(1)
    except AttributeError:
        log("The bag name is not in the expected format, aip-id_bag. Processing stopped.")
        move_error("bag_name", item)
        aips_errors += 1
        continue

    # Unpack the zip and/or tar file, resulting in the bag directory. Stops processing this AIP if the bag is invalid.
    try:
        unpack(item, aip_bag)
    except ValueError:
        log("\nThe unpacked bag is not valid. Processing stopped.")
        move_error("unpacked_bag_not_valid", aip_bag)
        aips_errors += 1
        continue

    # Validates the AIP against the APTrust size requirement. Stops processing this AIP if it is too big (above 5 TB).
    size_ok = size_check(aip_bag)
    if not size_ok:
        log("This AIP is above the 5TB limit and must be split. Processing stopped.")
        move_error("bag_too_big", aip_bag)
        aips_errors += 1
        continue

    # Validates the AIP against the APTrust character length requirements for directories and files.
    # If any are too long (over 255 characters), produces a list for staff review and stops processing this AIP.
    length_ok = length_check(aip_bag)
    if not length_ok:
        log("This AIP has at least one file or directory above the 255 character limit. Processing stopped.")
        move_error("name_too_long", aip_bag)
        aips_errors += 1
        continue

    # Updates the bag metadata files to meet APTrust requirements.
    # Do this step prior to renaming impermissible characters so that the path to the preservation.xml is not changed.
    try:
        add_bag_metadata(aip_bag)
    except FileNotFoundError:
        log("This AIP does not have a preservation.xml file. Processing stopped.")
        move_error("no_preservationxml", aip_bag)
        aips_errors += 1
        continue
    except ValueError as error:
        log(f"This AIP is missing required {error.args[0]} field in the preservation.xml. Processing stopped.")
        move_error("incomplete_preservationxml", aip_bag)
        aips_errors += 1
        continue

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
        move_error("updated_bag_not_valid", new_bag_name)
        aips_errors += 1
        exit()

    # Tars the bag.
    tar_bag(new_bag_name)

    # Logs the completion of processing of the AIP.
    log("Processing complete for this AIP.")
    aips_converted += 1

# Logs the end of the script, including the number of AIPs successfully converted and that had errors.
log(f"\nScript completed at {datetime.datetime.today()}")
log(f"{aips_converted} AIPs were successfully converted.")
log(f"{aips_errors} AIPs had errors and could not be converted.")
