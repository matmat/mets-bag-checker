# mets-bag-checker
METS Bag checker is a simple python tool to check the validitiy of their METS Information Packages (XML validity, completeness, Data Objects fixity, absence of unreferenced files).
## Description
METS Bag checker is a simple python tool to help METS implementers with little IT resources checking the validitiy of their Information Packages (below abbreviated as "IP(s)"). The term "bag" refers to the [BagIt standard (RFC 8493)](https://www.rfc-editor.org/rfc/rfc8493), as this tool is based on some basic rules, similar to those defined by BagIt, in order to perform checks on IPs.

Please be forgiving: this is my first real project in python (and in code in general).
## Pre-requisites
[Metadata Encoding and Transmission Standard (METS)](https://www.loc.gov/standards/mets/) is a metadata standard for packaging metadata of different types in a single XML file to describe a digital object at different levels of precision. It is not, though, a packaging standard like BagIt, though its `//mets:fileSec` element provides enough information to act as a manifest: a list of packaged files associated with a hash value.

This tool is based on the following conditions and packaging conventions (rather commonly implemented when using METS as a metadata standard for Information Packages, e.g., the [METS rules for digitization produced by the National library of France](https://www.bnf.fr/fr/les-referentiels-de-numerisation-de-la-bnf#bnf-enrichissement-des-m-tadonn-es):
* The METS file is well-formed;
* The Information Package is a directory identified by the presence of a METS file located at its root (support for ZIP or TAR files could be added in the future);
* The location of Data Objects (files referenced from the `//mets:fileSec` element) in the `//mets:file/@xlink:href` attribute is expressed by a relative path from the root directory of the package;
* For each `//mets:file` element, attributes `@CHECKSUM` and `@CHECKSUMTYPE` are provided;
* The number of supported algorithms is limited, hence `@CHECKSUMTYPE` attributes' value are one of `MD5`, `SHA-1`, `SHA-256`, `SHA-384`, `SHA-512`.

## Checks performed by the tool
* **Validity check**: the METS file conforms to METS 1.XX;
* **Completeness check**: all files referenced in the `//mets:fileSec` are present at their expected location;
* **Fixity check**: the actual checksum of all files referenced in the `//mets:fileSec` is consistent with the value specified in the METS file;
* **Orphanness check**: the Information Package does not contain files that would not be referenced in the METS file.

## Use
METS Bag checker can be used in the following ways.
### GUI
The interface.py file creates an interface to perform batch checks on all METS files conforming to a certain filename or filename pattern located in a directory.

Run the interface.py file.

1. Choose the directory where your METS packages are located.
2. Specify the name of your METS manifests (the wildcard "*" is accepted).
3. Select the actions the tool should perform.
4. Click on "Launch the test".
5. When the test is completed, click on the button "Select the location for the report file." to save the report.

### Python module
The file mets.py can be used as a python module: run

`python3 mets.py \[path to the first manifest\] \[path to the second manifest\] ...`

It will perform all the different checks on each manifest it identified.