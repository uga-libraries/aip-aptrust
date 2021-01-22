# Purpose

Convert AIPs from the UGA Libraries' digital preservation storage (ARCHive) to AIPs that can be ingested into APTrust to have geographically-distant storage. To be valid for APTrust, the AIPs are checked for a if they meet APTrust requirements for maximum size and file name length, additional bag metadata is added, and impermissible characters are replaced with underscores. The result of this script is tar files ready to ingest into APTrust.

## Status

* The script is tested on Windows 10. It is only partially tested (tar commands) on a Mac.
* Resulted AIPs are validated by DART but have not successfully ingested to the demo site yet. 
* Staff had not had an opportunity to provide feedback.

## Workflow

This is a batch workflow, which undertakes the following steps on each AIP in a folder. If an anticipated error is encountered, it is added to the script log and the bag is moved to a folder named with the error to avoid further processing.

1. Unzip and untar the AIP, resulting in a bag.

2. Validate the bag against APTrust requirements. Stops processing if the limits are exceeded.
   * The entire bag must be under 5 TB.
   * No file or directory name can exceed 255 characters, including extension.
   
3. Add fields to the bagit-info.txt file using default values or information from the preservation.xml file in the AIP.

4. Add an additional metadata file, aptrust-info.txt, to the bag. the metadata file uses default values or information from the preservation.xml file in the AIP.

5. Replaces invalid characters in file and directory names (cannot start with a dash or include five whitespace characters) with underscores and creates a log of name changes. This is done after updating the bag metadata so that the path to the preservation.xml file is not changed.

6. Validate and tar the bag.

## Explanation of fields added to bagit.info.txt:

* Source-Organization: APTrust subgroup name (University of Georgia)
* Internal-Sender-Description: ARCHive group, to differentiate between departments
* Internal-Sender-Identifier: the AIP ID, which is everything from the bag name except the "_bag" suffix
* Bag-Group-Identifier: the archival collection the AIP is part of or default text indicating it is not part of a collection

## Explanation of fields used in aptrust-info.txt:

* Title: Title of AIP in ARCHive
* Description: ?????
* Access: rights information in APTrust (Institution)
* Storage-Option: storage type to use in APTrust (Deep Archive)

## Workflow decisions to be made by staff

* APTrust overwrites old AIPs with a new version. Do we want all versions or just most recent in APTrust?
* Changes to the log structure (csv?) or content (more or less info) or name (date?)?
* Save the name change log to the AIP metadata folder?
* Use of fields, especially description, in bagit-info.txt and aptrust-info.txt?
* Ok with replacing those characters with underscores? Unlikely to come up unless someone starts an AIP with dash
* Delete the bag and just have the final tar files or helpful to have unpacked for review? Currently not deleted.