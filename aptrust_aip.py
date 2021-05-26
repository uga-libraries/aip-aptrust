# For pilot collaboration on digital preservation storage with Emory.
# Batch transforms AIPs from ARCHive into AIPs compatible with APTrust.
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


def move_error(error_name, aip_path, aip_name):
    """Moves the AIP to an error folder, named with the error type, so it is clear what step the AIP stopped on.
    Makes the error folder if it does not already exist prior to moving the AIP. """

    if not os.path.exists(f"errors/{error_name}"):
        os.makedirs(f"errors/{error_name}")
    os.replace(aip_path, f"errors/{error_name}/{aip_name}")


def unpack(aip_zip):
    """Unzips (if applicable) and untars the AIP, using different commands for Windows or Mac/Linux. The result is
    the AIP's bag directory, named aip_path-id_bag, which is saved to a folder named aptrust-aips within the AIPs
    directory. The original tar and zip files remain in the AIPs directory in case the script needs to be run again. """

    # Gets the operating system, which determines the command for unzipping and untarring.
    operating_system = platform.system()

    # For Windows, use 7-Zip to extract the files. If the AIP is both tarred and zipped, the command is run twice.
    if operating_system == "Windows":

        # Extracts the contents of the zip file, which is a tar file.
        # Tests if there is a zip file first since some AIPs are just tarred and not zipped.
        if aip_zip.endswith(".bz2"):
            subprocess.run(f'7z x {aip_zip}', stdout=subprocess.DEVNULL, shell=True)

        # Extracts the contents of the tar file, which is the AIP's bag directory.
        # Saves the bag to a folder within the AIPs directory named aptrust-aips.
        aip_tar = aip_zip.replace(".bz2", "")
        aip_tar_path = os.path.join(aips_directory, aip_tar)
        subprocess.run(f'7z x "{aip_tar_path}" -o{os.path.join(aips_directory, "aptrust-aips")}',
                       stdout=subprocess.DEVNULL, shell=True)

        # Deletes the tar file if there is also a zipped version of the AIP.
        # This is only necessary for Windows, since in Mac/Linux the intermediate tar file is not saved separately.
        # Now the AIPs directory only has the original ARCHive AIPs again, plus a folder with the unpacked bags.
        if aip_zip.endswith(".bz2"):
            os.remove(os.path.join(aips_directory, aip_zip.replace(".bz2", "")))

    # For Mac and Linux, use tar to extract the AIP's bag directory.
    # This command works if the AIP is tarred and zipped or if it is just tarred.
    # Makes the aptrust-aips directory to save the bag to, if it doesn't already exist, before extracting.
    else:
        if not os.path.exists("aptrust-aips"):
            os.makedirs("aptrust-aips")
        subprocess.run(f'tar -xf "{aip_zip}" -C aptrust-aips', shell=True)


def size_check(aip_path):
    """Tests if the AIP's bag is smaller than the limit of 5 TB and returns True or False. """

    # Variable for calculating the total bag size.
    bag_size = 0

    # Adds the size of all the bag metadata files.
    for file in os.listdir(aip_path):
        if file.endswith('.txt'):
            bag_size += os.path.getsize(f"{aip_path}/{file}")

    # Adds the bag payload size (the size of everything in the bag data folder) to the bag size.
    bag_info = open(f"{aip_path}/bag-info.txt", "r")
    for line in bag_info:
        if line.startswith("Payload-Oxum"):
            payload = line.split()[1]
            bag_size += float(payload)

    # Evaluates if the size is below the 5 TB limit and return the result (True or False).
    return bag_size < 5000000000000


def length_check(aip_path, aip_name):
    """Tests if all file and directory name lengths are at least one character but no more than 255 characters.
    Returns True if all names are within the limits or False if any names are outside the limits. Also creates a
    document with any names that are outside the limits for staff review. """

    # Makes a list to store lists with the path, name, and number of characters for each name outside the limits.
    # Each name's list will become a row in the character_limit_errors.csv.
    wrong_length = []

    # Checks the length of the AIP (top level folder).
    # If it is too long or 0, adds it to the wrong_length list.
    # Checking the AIP instead of root because everything in root except the AIP is also included in directories.
    if len(aip_name) > 255 or len(aip_name) == 0:
        wrong_length.append([aip_path, aip_name, len(aip_name)])

    # Checks the length of every directory and file.
    # If any name is too long or 0, adds it to the wrong_length list.
    for root, directories, files in os.walk(aip_path):
        for directory in directories:
            if len(directory) > 255 or len(directory) == 0:
                path = os.path.join(root, directory)
                wrong_length.append([path, directory, len(directory)])
        for file in files:
            if len(file) > 255 or len(file) == 0:
                path = os.path.join(root, file)
                wrong_length.append([path, file, len(file)])

    # If any names were too long or 0, saves them to a CSV in the AIPs directory for staff review.
    # The CSV is moved to the error folder with the bag once the error folder is made.
    # Also returns False if any names were the incorrect length or True if all lengths were correct.
    if len(wrong_length) > 0:
        with open(f"{aip_name}_character_limit_log.csv", "a", newline='') as result:
            writer = csv.writer(result)
            writer.writerow(["Path", "Name", "Length of Name"])
            for name_list in wrong_length:
                writer.writerow(name_list)
        return False
    else:
        return True


def character_check(aip_path, aip_name):
    """Tests if there are any impermissible characters in file and directory names. Names must not start with a dash
    or contain a newline, carriage return, tab, vertical tab, or ascii bell. Returns True if all name characters are
    permitted or False if not. Also creates a document with any names that include impermissible characters for staff
    review.

    Future development idea: if this happens enough, could add which character(s) were found. Right now, just returns
    False as soon as the first impermissible character is found."""

    def name_check(name):
        """Tests if a single file or directory name includes any impermissible characters. Returns True or False. """

        # Checks if the name starts with a dash (not permitted).
        if name.startswith("-"):
            return False

        # Checks if the name includes any characters that are not permitted.
        not_permitted = ["\n", "\r", "\t", "\v", "\a"]
        for character in not_permitted:
            if character in name:
                return False

        # If neither of the previous code blocks returned False, then all characters in the name are permitted.
        return True

    # Makes a list for file or directory names, including their full path, that contain impermissible characters.
    name_errors = []

    # Checks the AIP name and adds it to the name_errors list if there are impermissible characters.
    # Checking the AIP instead of root because everything in root except the AIP is checked as part of directories.
    if name_check(aip_name) is False:
        name_errors.append(os.path.join("aptrust-aips", aip_name))

    # Checks every directory and file name in the AIP. If there are impermissible characters, calculates the full
    # path for that directory or file and adds it to the name_errors list .
    for root, directories, files in os.walk(aip_path):
        for file in files:
            if name_check(file) is False:
                name_errors.append(os.path.join(root, file))
        for directory in directories:
            if name_check(directory) is False:
                name_errors.append(os.path.join(root, directory))

    # If any names have impermissible characters, saves them to a CSV in the AIPs directory for staff review.
    # Saves as a CSV even though there is only one column to make it faster to open in a spreadsheet for analysis.
    # This is saved in the AIPs directory but is moved to the error folder with the bag once the error folder is made.
    # Also returns False if impermissible characters were found or True if all characters are permitted.
    if len(name_errors) > 0:
        with open(f"{aip_name}_impermissible_characters_log.csv", "a", newline='') as result:
            writer = csv.writer(result)
            writer.writerow(["Name with Impermissible Characters"])
            for name_path in name_errors:
                writer.writerow([name_path])
        return False
    else:
        return True


def add_bag_metadata(aip_path, aip_name):
    """Adds additional fields to bagit-info.txt and adds a new file aptrust-info.txt to the bag metadata. The values
    for the metadata fields are either consistent for all UGA AIPs or are extracted from the preservation.xml file
    that is in the AIP's metadata folder. """

    # Namespaces that find() will use when navigating the preservation.xml.
    ns = {"dc": "http://purl.org/dc/terms/", "premis": "http://www.loc.gov/premis/v3"}

    # Reads the data from the AIP metadata file, which may be named aip-id_preservation.xml or aip-id_master.xml.
    # If the preservation.xml is not found, raises an error so the script can stop processing this AIP.
    try:
        tree = et.parse(f"{aip_path}/data/metadata/{aip_name.replace('_bag', '')}_preservation.xml")
        root = tree.getroot()
    except FileNotFoundError:
        try:
            tree = et.parse(f"{aip_path}/data/metadata/{aip_name.replace('_bag', '')}_master.xml")
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
        title = root.find("dc:title", ns).text
    except (et.ParseError, AttributeError):
        raise ValueError("dc:title")

    # Gets the collection id from the value of the first relatedObjectIdentifierValue in the aip_path section.
    # If there is no collection id (e.g. for some web archives), supplies default text.
    id = "aip/premis:object/premis:relationship/premis:relatedObjectIdentifier/premis:relatedObjectIdentifierValue"
    try:
        collection = root.find(id, ns).text
    except (et.ParseError, AttributeError):
        collection = "This AIP is not part of a collection."

    # For DLG newspapers, the first relationship is dlg and the second is the collection.
    # Updates the value of collection to be the text of the second relationship instead.
    if collection == "dlg":
        id = "aip/premis:object/premis:relationship[2]/premis:relatedObjectIdentifier/premis:relatedObjectIdentifierValue"
        collection = root.find(id, ns).text

    # Adds the required fields to bagit-info.txt.
    bag = bagit.Bag(aip_path)
    bag.info['Source-Organization'] = "University of Georgia"
    bag.info['Internal-Sender-Description'] = f"UGA unit: {group}"
    bag.info['Internal-Sender-Identifier'] = aip_name.replace("_bag", "")
    bag.info['Bag-Group-Identifier'] = collection

    # Makes aptrust-info.txt.
    with open(f"{aip_path}/aptrust-info.txt", "w") as new_file:
        new_file.write(f"Title: {title}\n")
        new_file.write("Access: Institution\n")
        new_file.write("Storage-Option: Glacier-Deep-OR\n")

    # Saves the bag, which updates the tag manifests with the new file aptrust-info.txt and the new checksums for the
    # edited file bagit-info.txt so the bag remains valid.
    bag.save(manifests=True)


def tar_bag(aip_path):
    """Tars the bag, using the appropriate command for Windows (7zip) or Mac/Linux (tar) operating systems."""

    # Gets the operating system, which determines the command for unzipping and untarring.
    operating_system = platform.system()

    # Gets the absolute path to the bag.
    bag_path = os.path.join(aips_directory, aip_path)

    # Tars the AIP using the operating system-specific command, 7-zip for Windows and tar for Mac/Linux.
    if operating_system == "Windows":
        subprocess.run(f'7z -ttar a "{aip_path}.tar" "{bag_path}"', stdout=subprocess.DEVNULL, shell=True)
    else:
        subprocess.run(f'tar -cf "{aip_path}.tar" "{aip_path}"', shell=True)


def log(log_path, log_row):
    """Adds a line to the script progress log."""

    with open(log_path, "a", newline="") as log_file:
        log_writer = csv.writer(log_file)
        log_writer.writerow(log_row)


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

# Tracks the number of AIPs fully transformed or with errors for making a summary of the script's success.
# Records the script start time to later calculate how long the script took to run.
aips_transformed = 0
aips_errors = 0
script_start = datetime.datetime.today()

# Saves the log path to a variable, for use throughout the script.
# If the log doesn't exist from earlier batches in the same day, adds a header row.
log_path = f"AIP_Transformation_Log_{script_start.date()}.csv"
if not os.path.exists(os.path.join(aips_directory, log_path)):
    log(log_path, ["AIP", "Errors", "Transformation Result"])

# Gets each AIP in the AIPs directory and transforms it into an APTrust-compatible AIP.
# Any AIP with an anticipated error is moved to a folder with the error name so processing can stop on that AIP.
for item in os.listdir():

    # Skip anything in the AIPs directory that isn't an AIP, such as the log, based on the file extension.
    if not (item.endswith(".tar.bz2") or item.endswith(".tar")):
        continue

    # Prints script progress to show it is still working.
    print("Starting transformation of:", item)

    # Calculates the bag name (aip-id_bag) from the file name for referring to the AIP after it is untarred/unzipped.
    # Stops processing this AIP if the bag name does not match the expected pattern.
    try:
        regex = re.match("^(.*_bag).", item)
        aip_bag_name = regex.group(1)
    except AttributeError:
        log(log_path, [item, "Bag name is not formatted aip-id_bag", "Incomplete"])
        move_error("bag_name", item, item)
        aips_errors += 1
        continue

    # Unpacks the AIP's bag directory from the zip and/or tar file.
    # The original zip and/or tar file is retained in case the script needs to be run again.
    unpack(item)

    # Variable that combines the aip_bag_name with the folder within the AIPs directory that it was saved to.
    aip_bag_path = os.path.join("aptrust-aips", aip_bag_name)

    # Validates the unpacked bag in case there was a problem during storage or unpacking.
    # Stops processing this AIP if the bag is invalid.
    try:
        aip_bagit_object = bagit.Bag(aip_bag_path)
        aip_bagit_object.validate()
    except bagit.BagValidationError as errors:
        log(log_path, [item, f"The unpacked bag is not valid: {errors}", "Incomplete"])
        move_error("unpacked_bag_not_valid", aip_bag_path, aip_bag_name)
        aips_errors += 1
        continue

    # Validates the AIP against the APTrust size requirement.
    # Stops processing this AIP if it is too big (above 5 TB).
    size_ok = size_check(aip_bag_path)
    if not size_ok:
        log(log_path, [item, "Above the 5TB limit", "Incomplete"])
        move_error("bag_size_limit", aip_bag_path, aip_bag_name)
        aips_errors += 1
        continue

    # Validates the AIP against the APTrust character length requirements for directories and files.
    # Produces a list for staff review and stops processing this AIP if any are 0 characters or more than 255.
    # the list is moved to the error folder, along with the bag, once the error folder is made.
    length_ok = length_check(aip_bag_path, aip_bag_name)
    if not length_ok:
        log(log_path, [item, "Name(s) outside the character limit", "Incomplete"])
        move_error("character_limit", aip_bag_path, aip_bag_name)
        log_name = f"{aip_bag_name}_character_limit_log.csv"
        os.replace(log_name, os.path.join("errors", "character_limit", log_name))
        aips_errors += 1
        continue

    # Validates the AIP against the APTrust character requirements for directories and files.
    # Produces a list for staff review and stops processing this AIP if any impermissible characters are found.
    # The list is moved to the error folder, along with the bag, once the error folder is made.
    characters_ok = character_check(aip_bag_path, aip_bag_name)
    if not characters_ok:
        log(log_path, [item, "Impermissible characters", "Incomplete"])
        move_error("impermissible_characters", aip_bag_path, aip_bag_name)
        log_name = f"{aip_bag_name}_impermissible_characters_log.csv"
        os.replace(log_name, os.path.join("errors", "impermissible_characters", log_name))
        aips_errors += 1
        continue

    # Updates the bag metadata files to meet APTrust requirements.
    try:
        add_bag_metadata(aip_bag_path, aip_bag_name)
    except FileNotFoundError:
        log(log_path, [item, "The preservation.xml is missing.", "Incomplete"])
        move_error("no_preservationxml", aip_bag_path, aip_bag_name)
        aips_errors += 1
        continue
    except ValueError as error:
        log(log_path, [item, f"The preservation.xml is missing the {error.args[0]}", "Incomplete"])
        move_error("incomplete_preservationxml", aip_bag_path, aip_bag_name)
        aips_errors += 1
        continue

    # Validates the bag in case there was a problem transforming it to an APTrust AIP.
    # Stops processing this AIP if the bag is invalid.
    try:
        aip_bagit_object = bagit.Bag(aip_bag_path)
        aip_bagit_object.validate()
    except bagit.BagValidationError as errors:
        log(log_path, [item, f"The transformed bag is not valid: {errors}", "Incomplete"])
        move_error("transformed_bag_not_valid", aip_bag_path, aip_bag_name)
        aips_errors += 1
        exit()

    # Tars the bag. The tar file is saved to the same folder as the bag (aptrust-aips) within the AIPs directory.
    tar_bag(aip_bag_path)

    # Updates the log for the successfully transformed AIP.
    log(log_path, [item, "n/a", "Complete"])
    aips_transformed += 1

# Prints summary information about the script's success.
script_end = datetime.datetime.today()
print(f"\nScript completed at {script_end}")
print(f"Time to complete: {script_end - script_start}")
print(f"{aips_transformed + aips_errors} AIPs were processed.")
print(f"{aips_transformed} AIPs were successfully transformed and {aips_errors} AIPs had errors.")
