# Use APTrust Partner Tools to validate and upload a batch of AIPs which are all in the same folder (AIPs directory).

# Script usage: python path/batch_validate.py aptrust_type path/aips_directory path/partner_tools
#   aptrust_type is production or demo
#   aips_directory is the folder with the AIPs to be uploaded
#   partner_tools is the folder with the APTrust Partner Tools

import csv
import datetime
import os
import subprocess
import sys


def validate_arguments(arguments_list):
    """Verifies the three required arguments were provided for running the script: a path to the APTrust partner
    tools, a path to the AIPs directory, and if the AIPs are to be uploaded to production or demo. If any are missing
    or not an expected value, prints an error message and quits the script. If they are present, makes the AIPs
    directory the current directory and calculates additional paths. """

    # The script usage information is used in many error statements.
    script_usage = "Script usage: python path/batch_validate.py aptrust_type path/aips_directory path/partner_tools"

    # Checks for any missing or extra arguments.
    if len(arguments_list) != 4:
        print(f"The incorrect number of script arguments was provided.\n{script_usage}")
        exit()

    # Exits the script if the provided APTrust type is not one of the two expected values, production or demo.
    aptrust_type = arguments_list[1]
    if aptrust_type not in ("production", "demo"):
        print(f'The APTrust type must be "production" or "demo".\n{script_usage}')
        exit()

    # Makes the provided path to the AIPs directory the current directory.
    # Exits the script if it does not exist or it is a file instead of a directory.
    aips_directory = arguments_list[2]
    try:
        os.chdir(aips_directory)
    except (FileNotFoundError, NotADirectoryError):
        print(f"The AIPs directory path is incorrect.\n{script_usage}")
        exit()

    # Make paths to specific tools and files with the provided path to the partner tools.
    # Exits the script if any do not exist.
    tools_path = arguments_list[3]
    apt_validate_path = os.path.join(tools_path, "apt_validate.exe")
    apt_upload_path = os.path.join(tools_path, "apt_upload.exe")
    config_validate_path = os.path.join(tools_path, "aptrust_bag_validation_config.json")
    credentials_path = os.path.join(tools_path, f"{aptrust_type}.conf")

    for path in (tools_path, apt_validate_path, apt_upload_path, config_validate_path, credentials_path):
        if not os.path.exists(path):
            print(f"{path} is incorrect.\n{script_usage}")
            exit()

    return apt_validate_path, apt_upload_path, config_validate_path, credentials_path


def log(log_row):
    """Add a row of text to the upload log for later staff review."""

    with open("aptrust_upload_log.csv", "a", newline="") as log_file:
        log_writer = csv.writer(log_file)
        log_writer.writerow(log_row)


# Validates the script arguments and quits the script if there are any errors.
# Otherwise, changes the current directory to the AIPs directory the current directory, and gets tool and file paths.
apt_validate, apt_upload, config_validate, credentials = validate_arguments(sys.argv)

# Start tracking counts for summarizing script results.
total_aips = 0
validation_errors = 0
upload_errors = 0

# Starts a log, if it doesn't already exist from uploading a previous batch of AIPs.
if not os.path.exists("aptrust_upload_log.csv"):
    log(["AIP", "Validation", "Validation Date", "Validation Errors", "Upload", "Upload Date", "Upload Errors"])

# Validate each AIP and upload it to APTrust if it is valid.
for item in os.listdir("."):

    # Skips anything in the AIPs directory that is not an AIP (tar file), like bag directories or log files.
    if not item.endswith(".tar"):
        continue

    # Prints the current AIP to show the script's progress and updated total AIPs counter.
    print("Starting on:", item)
    total_aips += 1

    # Validates the AIP using the Partner Tool apt_validate.
    result = subprocess.run(f'{apt_validate} --config={config_validate} "{os.path.join(os.getcwd(), item)}"',
                            capture_output=True, shell=True)

    # If the AIP is valid, starts a list to be used for the log once the upload result is obtained.
    # Otherwise, does not upload. Adds this AIP to the log, updates the error counter, and starts on the next AIP.
    if result.returncode == 0:
        to_log = [item, "Valid", datetime.datetime.today(), "n/a"]
    else:
        log([item, f"Not Valid: {result.returncode}", datetime.datetime.today(),
             result.stdout.decode('UTF-8').replace("\n", "; "), "n/a", "n/a", "n/a"])
        validation_errors += 1
        continue

    # Run apt_load.
    result = subprocess.run(f'{apt_upload} --config={credentials} --key="{item}" "{os.path.join(os.getcwd(), item)}"',
                            capture_output=True, shell=True)

    # Adds this AIP to the log. If there was an error, updates the error counter.
    if result.returncode == 0:
        to_log.extend(["Upload Complete", datetime.datetime.today(), "n/a"])
    else:
        to_log.extend([f"Upload Error: {result.returncode}", datetime.datetime.today(),
                       result.stdout.decode('UTF-8').replace("\n", "; ")])
        upload_errors += 1
    log(to_log)

# Print a summary of the script results.
print(f"\nScript is complete, with {total_aips} AIPs processed.")
print(validation_errors, "AIPs had validation errors.")
print(upload_errors, "AIPs had upload errors.")
