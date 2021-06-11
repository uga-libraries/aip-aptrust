# APTrust Transformation: No Zip Branch
## Purpose

Transform AIPs from the UGA Libraries' digital preservation system (ARCHive) to AIPs that can be ingested into APTrust to have geographically-distant storage. The AIPs are checked for if they meet APTrust requirements for maximum size and file/directory name length, additional bag metadata is added, and impermissible characters are replaced with underscores. The result of this script is bags that are ready to be tarred and then ingested into APTrust.

Use this branch of the script for AIPs over 20 GB, where unzipping as part of the script is currently too slow. For smaller AIPs, use the main branch, which incorporates unzipping and tarring into the script.

## Dependencies

Install the bagit-python: pip install bagit

For Windows, install 7-Zip [https://www.7-zip.org/download.html](https://www.7-zip.org/download.html)

## Workflow

1. Unzip and untar each AIP. In Windows, this can be done by selecting all the files in Windows Explorer, right clicking, selecting 7-Zip, and clicking "Extract Here". This will need to be done twice, once with the bz2 files and once with the resulting tar files. The end result is AIP bag directories.


2. Run the aptrust_aip.py script. ```python aptrust_aip.py aips_directory```
   
The script undertakes the following steps on each AIP in the AIPs directory. If an anticipated error is encountered, the bag is moved to a folder named with the error to avoid further processing.

   * Unzips and untars the AIP, resulting in a bag, and validates the bag.
   

   * Verifies the bag meets APTrust limits:
      * The entire bag must be under 5 TB.
      * No file or directory name can be 0 characters or exceed 255 characters.
      * No file or directory name can start with a dash or include a newline, carriage return, tab, vertical tab, or ascii bell. 
   

   * Adds metadata fields to the bagit-info.txt file using default values or information from the preservation.xml file in the AIP.


   * Adds a new file, aptrust-info.txt, to the bag metadata files. The aptrust-info.txt file uses default values or information from the preservation.xml file in the AIP.


   * Validates the bag.

The script also creates a log (a CSV) with the name of each AIP, if any renaming is done, output from any anticipated errors that were encountered, and if the AIP was successfully transformed. Information for an AIP is saved to this log when an anticipated error is encountered or after transformation is complete.

3. Tar each of the AIP bag directories. In Windows, copy the "zipall.cmd" file to the AIPs directory and double click the file to tar each of the bags in one batch.

## Explanation of fields added to bagit.info.txt

* **Source-Organization:** APTrust subgroup name (University of Georgia)
* **Internal-Sender-Description:** ARCHive group, to differentiate between departments
* **Internal-Sender-Identifier:** the AIP ID
* **Bag-Group-Identifier:** the archival collection the AIP is part of or default text if it is not part of a collection

## Explanation of fields in aptrust-info.txt

* **Title:** Title of the AIP in ARCHive
* **Access:** who can view AIP metadata in APTrust (Institution)
* **Storage-Option:** storage type to use in APTrust (Glacier-Deep-OR)
