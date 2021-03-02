## Purpose

Transform AIPs from the UGA Libraries' digital preservation system (ARCHive) to AIPs that can be ingested into APTrust to have geographically-distant storage. The AIPs are checked for if they meet APTrust requirements for maximum size and file/directory name length, additional bag metadata is added, and impermissible characters are replaced with underscores. The result of this script is tar files ready to ingest into APTrust.

## Dependencies

Install the bagit-python: pip install bagit

For Windows, install 7-Zip [https://www.7-zip.org/download.html](https://www.7-zip.org/download.html)

## Workflow

This is a batch workflow, which undertakes the following steps on each AIP in a folder. If an anticipated error is encountered, the bag is moved to a folder named with the error to avoid further processing.

1. Unzips and untars the AIP, resulting in a bag, and validates the bag.

2. Verifies the bag meets APTrust limits.
   * The entire bag must be under 5 TB.
   * No file or directory name can be 0 characters or exceed 255 characters.
   * No file or directory name can start with a dash or include a newline, carriage return, tab, vertical tab, or ascii bell. 
   
3. Adds metadata fields to the bagit-info.txt file using default values or information from the preservation.xml file in the AIP.

4. Adds a new file, aptrust-info.txt, to the bag metadata files. The aptrust-info.txt file uses default values or information from the preservation.xml file in the AIP.

5. Validates and tars the bag.

The script also creates a log (a CSV) with the name of each AIP, if any renaming is done, output from any anticipated errors that were encountered, and if the AIP was successfully transformed. Information for an AIP is saved to this log when an anticipated error is encountered or after transformation is complete.

### Explanation of fields added to bagit.info.txt

* **Source-Organization:** APTrust subgroup name (University of Georgia)
* **Internal-Sender-Description:** ARCHive group, to differentiate between departments
* **Internal-Sender-Identifier:** the AIP ID
* **Bag-Group-Identifier:** the archival collection the AIP is part of or default text if it is not part of a collection

### Explanation of fields used in aptrust-info.txt

* **Title:** Title of the AIP in ARCHive
* **Access:** who can view AIP metadata in APTrust (Institution)
* **Storage-Option:** storage type to use in APTrust (Glacier-Deep-OR)
