# For pilot collaboration on digital preservation storage with Emory.
# Batch converts AIPs from ARCHive into AIPs compatible with APTrust.
# Prior to running this script, export the AIPs from ARCHive and save to a folder (AIPs directory).

# Script usage: python /path/aptrust_aip.py /path/aips_directory

import bagit
import csv
import datetime
import os
import platform
import re
import subprocess
import sys
import xml.etree.ElementTree as et


def move_error(error_name, aip, aip_name):
    """Moves the AIP folder to an error folder, named with the error type, so it is clear what step the AIP stopped on.
    Makes the error folder if it does not already exist prior to moving the AIP folder. """

    if not os.path.exists(f"errors/{error_name}"):
        os.makedirs(f"errors/{error_name}")
    os.replace(aip, f"errors/{error_name}/{aip_name}")


def unpack(aip_zip):
    """Unzips (if applicable) and untars the AIP, using different commands for Windows or Mac/Linux. The result is
    the AIP's bag directory, named aip-id_bag, which is saved to a folder named aptrust-aips within the AIPs
    directory. The original tar and zip files remain in the AIPs directory in case the script needs to be run again. """

    # Gets the operating system, which determines the command for unzipping and untarring.
    operating_system = platform.system()

    # For Windows, use 7-Zip to extract the files. If the AIP is both tarred and zipped, the command is run twice.
    if operating_system == "Windows":

        # Extracts the contents of the zip file, which is a tar file.
        # Tests if there is a zip file first since some AIPs are just tarred and not zipped.
        if aip_zip.endswith(".bz2"):
            subprocess.run(f'7z x {aip_zip}', stdout=subprocess.DEVNULL, shell=True)

        # Extracts the contents of the tar file, which is the AIP's bag directory,
        # and saves the bag to a folder within the AIPs directory named aptrust-aips.
        # Calculates the name of the tar file by removing the .bz2 extension, if present, to be able to extract.
        aip_tar = aip_zip.replace(".bz2", "")
        aip_tar_path = os.path.join(aips_directory, aip_tar)
        subprocess.run(f'7z x "{aip_tar_path}" -o{os.path.join(aips_directory, "aptrust-aips")}',
                       stdout=subprocess.DEVNULL, shell=True)

    # For Mac and Linux, use tar to extract the AIP's bag directory.
    # This command works if the AIP is tarred and zipped or if it is just tarred.
    # TODO: indicate destination directory for the unpacked bag.
    else:
        subprocess.run(f"tar -xf {aip_zip}", shell=True)


def size_check(aip):
    """Tests if the bag is smaller than the limit of 5 TB and returns True or False. """

    # Variable for calculating the total bag size.
    bag_size = 0

    # Adds the size of all the bag metadata files.
    for file in os.listdir(aip):
        if file.endswith('.txt'):
            bag_size += os.path.getsize(f"{aip}/{file}")

    # Adds the bag payload size (the size of everything in the bag data folder) to the bag size.
    bag_info = open(f"{aip}/bag-info.txt", "r")
    for line in bag_info:
        if line.startswith("Payload-Oxum"):
            payload = line.split()[1]
            bag_size += float(payload)

    # Evaluate if the size is below the 5 TB limit and return the result (True or False).
    return bag_size < 5000000000000


def length_check(aip):
    """Tests if the file and directory name lengths are at least one character but no longer than 255 characters.
    Returns True if all names are within the limits or False if any names are outside the limit. Also creates a
    document with any names that are outside the limit for staff review. """

    # Makes a list to store tuples with the path and number of characters for any name outside the limits.
    wrong_length = []

    # Checks the length of the AIP (top level folder).
    # If it is too long or 0, adds it and its length to the wrong_length list.
    # Checking the AIP instead of root because everything in root except the AIP is also included in directories.
    if len(aip) > 255 or len(aip) == 0:
        wrong_length.append((aip, len(aip)))

    # Checks the length of every directory and file.
    # If any name is too long or 0, adds its full path and its length to the wrong_length list.
    for root, directories, files in os.walk(aip):
        for directory in directories:
            if len(directory) > 255 or len(directory) == 0:
                path = os.path.join(root, directory)
                wrong_length.append((path, len(directory)))
        for file in files:
            if len(file) > 255 or len(file) == 0:
                path = os.path.join(root, file)
                wrong_length.append((path, len(file)))

    # If any names were too long or 0, saves each of those names to a file for staff review and returns False so the
    # script stops processing this AIP. Otherwise, returns True so the next step can start on this AIP.
    if len(wrong_length) > 0:
        with open("character_limit_error.csv", "a", newline='') as result:
            writer = csv.writer(result)
            # Adds a header if the CSV is empty, meaning this is the first AIP with names with incorrect lengths.
            if os.path.getsize("character_limit_error.csv") == 0:
                writer.writerow(["Path", "Length of Name"])
            for name in wrong_length:
                writer.writerow([name[0], name[1]])
        return False
    else:
        return True


def add_bag_metadata(aip, aip_name):
    """Adds additional fields to bagit-info.txt and adds a new file aptrust-info.txt. The values for the metadata
    fields are either consistent for all UGA AIPs or are extracted from the preservation.xml file that is in the
    AIP's metadata folder. """

    # Namespaces that find() will use when navigating the preservation.xml.
    ns = {"dc": "http://purl.org/dc/terms/", "premis": "http://www.loc.gov/premis/v3"}

    # Parses the data from the preservation.xml.
    # If the preservation.xml is not found, raises an error so the script can stop processing this AIP.
    try:
        tree = et.parse(f"{aip}/data/metadata/{aip_name.replace('_bag', '')}_preservation.xml")
        root = tree.getroot()
    except FileNotFoundError:
        raise FileNotFoundError

    # For the next three try/except blocks, et.ParseError is from not finding the expected field in the preservation.xml
    # and AttributeError is from trying to get text from the variable for the missing field, which has a value of None.

    # Gets the group id from the value of the first objectIdentifierType (the ARCHive URI).
    # Starts at the 28th character to skip the ARCHive part of the URI and just get the group code.
    # If this field (which is required) is missing, raises an error so the script can stop processing this AIP.
    try:
        object_id_field = root.find("aip/premis:object/premis:objectIdentifier/premis:objectIdentifierType", ns)
        uri = object_id_field.text
        group = uri[28:]
    except (et.ParseError, AttributeError):
        raise ValueError("premis:objectIdentifierType")

    # Gets the title from the value of the title element.
    # If this field (which is required) is missing, raises an error so the script can stop processing this AIP.
    try:
        title_field = root.find("dc:title", ns)
        title = title_field.text
    except (et.ParseError, AttributeError):
        raise ValueError("dc:title")

    # Gets the collection id from the value of the first relatedObjectIdentifierValue in the aip section.
    # If there is no collection id (e.g. for some web archives), supplies default text.
    id_path = "aip/premis:object/premis:relationship/premis:relatedObjectIdentifier/premis:relatedObjectIdentifierValue"
    try:
        relationship_id_field = root.find(id_path, ns)
        collection = relationship_id_field.text
    except (et.ParseError, AttributeError):
        collection = "This AIP is not part of a collection."

    # For DLG newspapers, the first relationship is dlg and the second is the collection.
    # Updates the value of collection to be the text of the second relationship instead.
    if collection == "dlg":
        id = "aip/premis:object/premis:relationship[2]/premis:relatedObjectIdentifier/premis:relatedObjectIdentifierValue"
        collection = root.find(id, ns).text

    # Adds the required fields to bagit-info.txt.
    bag = bagit.Bag(aip)
    bag.info['Source-Organization'] = "University of Georgia"
    bag.info['Internal-Sender-Description'] = f"UGA unit: {group}"
    bag.info['Internal-Sender-Identifier'] = aip_name.replace("_bag", "")
    bag.info['Bag-Group-Identifier'] = collection

    # Makes aptrust-info.txt.
    with open(f"{aip}/aptrust-info.txt", "w") as new_file:
        new_file.write(f"Title: {title}\n")
        new_file.write("Description: TBD\n")
        new_file.write("Access: Institution\n")
        new_file.write("Storage-Option: Glacier-Deep-OR\n")

    # Saves the bag, which updates the tag manifests with the new file aptrust-info.txt and the new checksums for the
    # edited file bagit-info.txt so the bag remains valid.
    bag.save(manifests=True)


def update_characters(aip, aip_name):
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
        # Not permitted: newline, carriage return, tab, vertical tab, and ascii bells.
        not_permitted = ["\n", "\r", "\t", "\v", "\a"]
        for character in not_permitted:
            if character in new_name:
                new_name = new_name.replace(character, "_")

        # If the new name is different from the original name, renames the file or directory to the new name.
        # The default is to include the root as part of the path, but for AIPs (AIP is the root) just add aptrust-aips.
        # Also saves the original and new name to a list of changed names to use for making a record of the change.
        if not original == new_name:
            if join_root:
                changed_names.append((os.path.join(root, original), os.path.join(root, new_name)))
                os.replace(os.path.join(root, original), os.path.join(root, new_name))
            else:
                changed_names.append((os.path.join("aptrust-aips", original), os.path.join("aptrust-aips", new_name)))
                os.replace(os.path.join("aptrust-aips", original), os.path.join("aptrust-aips", new_name))

        # This is needed for AIPs only, so the script can continue to refer to the bag.
        return os.path.join("aptrust-aips", new_name)

    # Makes a list of tuples with the original and updated name so that they can be saved to a CSV later.
    # Values are added to this list within rename()
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

    # Updates the AIP name if it starts with a dash or contains impermissible characters.
    # Checking the AIP instead of root because everything in root except the AIP was updated as part of directories.
    new_aip_path = rename(aip_name, join_root=False)

    # Updates the bag manifests with the new names so it continues to be valid.
    # Note: bagit prints to the terminal that each renamed thing is not in the manifest, but the resulting bag is valid.
    bag = bagit.Bag(new_aip_path)
    bag.save(manifests=True)

    # If any names were changed, saves them to a CSV as a record of actions taken on the AIP. If the AIP name was
    # changed, the file and directory paths in the CSV will have the old name since the AIP name is changed last.
    if len(changed_names) > 0:
        with open("renaming.csv", "a", newline='') as result:
            writer = csv.writer(result)
            # Only adds a header if the document is new (empty).
            if os.path.getsize("renaming.csv") == 0:
                writer.writerow(["Original Name", "Updated Name"])
            for name in changed_names:
                writer.writerow([name[0], name[1]])

    # Creates a variable with a message for the log (if any names were changed or not).
    if len(changed_names) == 0:
        log_message = "No renaming"
    else:
        log_message = "Some renaming"

    # Returns the new_aip_name so the rest of the script can still refer to the bag and the log message.
    # In the vast majority of cases, this is still identical to the original AIP name.
    return new_aip_path, log_message


def tar_bag(aip):
    """Tars the bag, using the appropriate command for Windows (7zip) or Mac/Linux (tar) operating systems."""

    # Gets the operating system, which determines the command for unzipping and untarring.
    operating_system = platform.system()

    bag_path = os.path.join(aips_directory, aip)

    # Tars the AIP using the operating system-specific command.
    if operating_system == "Windows":
        subprocess.run(f'7z -ttar a "{aip}.tar" "{bag_path}"', stdout=subprocess.DEVNULL, shell=True)
    else:
        # TODO: confirm this updated path saves in the pre-existing aptrust-aips directory.
        subprocess.run(f'tar -cf {aip}.tar "{aip}"', shell=True)


# Gets the directory from the script argument. If it is missing, prints an error and quits the script.
try:
    aips_directory = sys.argv[1]
except IndexError:
    print("Missing the AIPs directory, which is a required script argument.")
    print("Script usage: python /path/aptrust_aip.py /path/aips_directory")
    exit()

# Makes the AIPs directory the current directory. If it is not a valid directory, prints an error and quits the script.
try:
    os.chdir(aips_directory)
except (FileNotFoundError, NotADirectoryError):
    print("The provided AIPs directory is not a valid directory:", aips_directory)
    print("Script usage: python /path/aptrust_aip.py /path/aips_directory")
    exit()

# Tracks the number of AIPs fully converted or with errors for making a summary of the script's success.
# Records the script start time to later calculate how long the script took to run.
aips_converted = 0
aips_errors = 0
script_start = datetime.datetime.today()

# Creates a CSV file in the AIPs directory for logging the script progress, including a header row.
# TODO: accommodate more than one batch in a day. Unique names for log? Append to existing log?
log = open(f"AIP_Conversion_Log_{script_start.date()}.csv", "w", newline="")
log_writer = csv.writer(log)
log_writer.writerow(["AIP", "Renaming", "Errors", "Conversion Result"])

# Gets each AIP in the AIPs directory and transforms it into an APTrust-compatible AIP.
# Any AIP with an anticipated error is moved to a folder with the error name so processing can stop on that AIP.
for item in os.listdir():

    # Skip anything in the AIPs directory that isn't an AIP, such as the log, based on the file extension.
    if not (item.endswith(".tar.bz2") or item.endswith(".tar")):
        continue

    # Starts a list of information to be added to the log for this AIP.
    # Saves the information to the log when a known error is encountered or conversion is complete.
    log_row = [item]
    print("Starting conversion of:", item)

    # Calculates the bag name (aip-id_bag) from the file name for referring to the AIP after the bag is extracted.
    # Stops processing this AIP if the bag name does not match the expected pattern.
    try:
        regex = re.match("^(.*_bag).", item)
        aip_bag_name = regex.group(1)
    except AttributeError:
        log_row.extend(["n/a", "The bag name is not formatted aip-id_bag.", "Not converted"])
        log_writer.writerow(log_row)
        move_error("bag_name", item, item)
        aips_errors += 1
        continue

    # Unpacks the AIP's bag directory from the zip and/or tar file.
    # The original zip and/or tar file is retained in case the script has errors and needs to be run again.
    unpack(item)

    # Variable that combines the aip_bag_name name with the folder within the AIPs directory that it was saved to.
    aip_bag_path = os.path.join("aptrust-aips", aip_bag_name)

    # Validates the unpacked bag in case there was a problem during storage or unpacking.
    # Stops processing this AIP if the bag is invalid.
    try:
        aip_bagit_object = bagit.Bag(aip_bag_path)
        aip_bagit_object.validate()
    except bagit.BagValidationError as errors:
        log_row.extend(["n/a", f"The unpacked bag is not valid: {errors}", "Not converted"])
        log_writer.writerow(log_row)
        move_error("unpacked_bag_not_valid", aip_bag_path, aip_bag_name)
        aips_errors += 1
        continue

    # Validates the AIP against the APTrust size requirement.
    # Stops processing this AIP if it is too big (above 5 TB).
    size_ok = size_check(aip_bag_path)
    if not size_ok:
        log_row.extend(["n/a", "This AIP is above the 5TB limit.", "Not converted"])
        log_writer.writerow(log_row)
        move_error("bag_too_big", aip_bag_path, aip_bag_name)
        aips_errors += 1
        continue

    # Validates the AIP against the APTrust character length requirements for directories and files.
    # Produces a list for staff review and stops processing this AIP if any are 0 characters or more than 255.
    length_ok = length_check(aip_bag_path)
    if not length_ok:
        log_row.extend(["n/a", "At least one name is outside the character limit.", "Not converted"])
        log_writer.writerow(log_row)
        move_error("name_length", aip_bag_path, aip_bag_name)
        aips_errors += 1
        continue

    # Updates the bag metadata files to meet APTrust requirements.
    # Does this step prior to renaming impermissible characters so that the path to the preservation.xml is not changed.
    try:
        add_bag_metadata(aip_bag_path, aip_bag_name)
    except FileNotFoundError:
        log_row.extend(["n/a", "The preservation.xml is missing.", "Not converted"])
        log_writer.writerow(log_row)
        move_error("no_preservationxml", aip_bag_path, aip_bag_name)
        aips_errors += 1
        continue
    except ValueError as error:
        log_row.extend(["n/a", f"The preservation.xml is missing the {error.args[0]}.", "Not converted"])
        log_writer.writerow(log_row)
        move_error("incomplete_preservationxml", aip_bag_path, aip_bag_name)
        aips_errors += 1
        continue

    # Checks the AIP for impermissible characters and replaces them with underscores.
    # Produces a list of changed names for the AIP's preservation record.
    # Saves the new name for the AIP bag in case it was altered by this function so the script can continue acting on
    # the bag. If UGA naming conventions are followed, it will almost always be the same as aip_bag_name.
    new_bag_path, log_text = update_characters(aip_bag_path, aip_bag_name)
    log_row.append(log_text)

    # Validates the bag in case there was a problem converting it to an APTrust AIP.
    # Stops processing this AIP if the bag is invalid.
    try:
        aip_bagit_object = bagit.Bag(new_bag_path)
        aip_bagit_object.validate()
    except bagit.BagValidationError as errors:
        log_row.extend(["n/a", f"The updated bag is not valid: {errors}", "Not converted"])
        log_writer.writerow(log_row)
        move_error("updated_bag_not_valid", new_bag_path, new_bag_path[13:])
        aips_errors += 1
        exit()

    # Tars the bag. The tar file is saved to a folder named "aptrust-aips" within the AIPs directory.
    tar_bag(new_bag_path)

    # Updates the log for the successfully converted AIP.
    log_row.extend(["No errors detected.", "Conversion completed"])
    log_writer.writerow(log_row)
    aips_converted += 1

# Prints summary information about script's success.
script_end = datetime.datetime.today()
print(f"\nScript completed at {script_end}")
print(f"Time to complete: {script_end - script_start}")
print(f"{aips_converted} AIPs were successfully converted.")
print(f"{aips_errors} AIPs had errors and could not be converted.")
