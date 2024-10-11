# mets-bag-checker
METS Bag checker is a simple python tool to check the validity of METS Information Packages (XML validity, completeness, Data Objects fixity, absence of unreferenced files).
## Description
METS Bag checker is a simple python tool to help METS implementers with little IT resources checking the validitiy of their Information Packages (below abbreviated as "IP(s)"). The term "bag" refers to the [BagIt standard (RFC 8493)](https://www.rfc-editor.org/rfc/rfc8493), as this tool is based on some basic rules, similar to those defined by BagIt, in order to perform checks on IPs.

## Pre-requisites
[Metadata Encoding and Transmission Standard (METS)](https://www.loc.gov/standards/mets/) is a metadata standard for packaging metadata of different types in a single XML file to describe a digital object at different levels of precision. It is not, though, a packaging standard like BagIt, though its `//mets:fileSec` element provides enough information to act as a manifest: a list of packaged files associated with a hash value.

This tool is based on the following conditions and packaging conventions (rather commonly implemented when using METS as a metadata standard for Information Packages, e.g., the [METS rules for digitization produced by the National library of France](https://www.bnf.fr/fr/les-referentiels-de-numerisation-de-la-bnf#bnf-enrichissement-des-m-tadonn-es)):
* The Information Package is a directory, zipped or not.
* The manifest name is the same in all Packages - or at least is predictable, according to a given pattern -;
* The Information Package contains a METS file;
* The location of Data Objects (files referenced from the `//mets:fileSec` element) in the `//mets:file/mets:FLocat/@xlink:href` attribute is expressed by a relative path from the root directory of the package;
* For each `//mets:file` element, attributes `@CHECKSUM` and `@CHECKSUMTYPE` are provided;
* The number of supported algorithms is limited, hence `@CHECKSUMTYPE` attributes' value are one of `MD5`, `SHA-1`, `SHA-256`, `SHA-384`, `SHA-512`.

The tool requires python 3.9 to work properly.

## Checks performed by the tool
* **Well-formedness check**: the METS file is well-formed XML;
* **Validity check**: the METS file conforms to METS 1.12.1;
* **Completeness check**: all files referenced in the `//mets:fileSec` are present at their expected location;
* **Fixity check**: the actual checksum of all files referenced in the `//mets:fileSec` is consistent with the value specified in the METS file;
* **Orphanness check**: the Information Package does not contain files that would not be referenced in the METS file.

## Use
METS Bag checker can be used in the following ways.
### GUI
The interface.py file creates an interface to perform batch checks on all METS files conforming to a certain filename pattern located in a directory.

Run the interface.py file.

1. Specify the filename pattern of your METS manifests according to the REGEX syntax (dots should be escaped: `\.`).
2. Specify the nature of the package (directory or ZIP/TAR container).
3. Choose the directories or ZIP/TAR files that you want to analyze. You can do this several times, directories or ZIP/TAR files will be added to the list. You can mix ZIP and TAR files (but not container files and directories).
4. Select the actions the tool should perform.
5. Click on "Launch the test".
6. When the test is completed, you can click on the button "Select the location for the report file." to save the report.
7. You can clear the list of packages to resume the selection process by clicking on "Clear list of IPs".

### Python module
The file mets.py can be used as a python module: run

`python3 mets.py [path to the package (directory of ZIP/TAR file)] [METS REGEX filename pattern]`

It will perform all the different checks.