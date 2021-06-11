# Use APTrust Partner Tools to validate and upload a batch of AIPs which are all in the same folder (AIPs directory).
# Script usage: python C:/path/batch_validate.py aptrust_type(production|demo) C:/path/aips_directory C:/path/partner_tools

import os
import sys


def validate_arguments(arguments_list):
    """Verifies the three required arguments were provided for running the script: a path to the APTrust partner
    tools, a path to the AIPs directory, and if the AIPs are to be uploaded to production or demo. If any are missing
    or not an expected value, prints an error message and quits the script. If they are present, makes the AIPs
    directory the current directory and calculates additional paths. """

    # The script usage information is used in many error statements.
    script_usage = "Script usage: python C:/path/batch_validate.py aptrust_type(production|demo) C:/path/aips_directory C:/path/partner_tools"

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


# Validates the script arguments and quits the script if there are any errors.
# Otherwise, changes the current directory to the AIPs directory the current directory, and gets tool and file paths.
apt_validate, apt_upload, config_validate, credentials = validate_arguments(sys.argv)

# Start tracking counts for summarizing script results.

# Start log.

# Validate each AIP and upload it to APTrust if it is valid.

    # Skip anything in the AIPs directory that is not an AIP (tar file).

    # Prints a progress message.

    # Run apt_validate.

    # Interpret apt_validate results.

        # Add results to log.

        # If not valid, start the next AIP.

    # Run apt_load.

    # Interpret apt_load results and add to log.

# Print a summary of the script results.