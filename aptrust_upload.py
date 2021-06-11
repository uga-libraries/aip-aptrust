# Use APTrust Partner Tools to validate and upload a batch of AIPs which are all in the same folder (AIPs directory).
# Script usage: python C:/path/batch_validate.py C:/path/partner_tools C:/path/aips_directory production|demo

# Validate script arguments. Make AIPS directory the current directory and make paths to tools to use.

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