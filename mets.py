#!/usr/bin/python3.10
# -*-coding:utf-8 -*

"""Module for batch validation of METS packages: XML validation, presence and
fixity of all referenced files, absence of unreferenced files)."""

from os import path
import glob
import sys

from lxml import etree
import hashlib


class METSFile:

    """This class is instantiated for each XML-METS file. It contains methods
    used to check the consistency of the manifest with the Information 
     package, i.e., the directory where the XML-METS file is located."""

    def __init__(self, path_to_mets_file) -> None:
        self.path_to_mets_file = path_to_mets_file
        self.directory = path.split(path_to_mets_file)[0]
        self.name = path.split(path_to_mets_file)[1]

        """Parses the XML file and returns an error if the XML file is not well-formed."""

        try:
            self.xml = etree.parse(self.path_to_mets_file)
        except etree.XMLSyntaxError:
            print(f"Le fichier {self.path_to_mets_file} n'est pas bien formé.", file=sys.stderr)


    def validate(self):

        """Validates the METS file against its XSD schema."""
        parsed_schema = etree.parse(path.join(path.split(__file__)[0], 'METSSchema/mets.xsd'))
        mets_schema = etree.XMLSchema(parsed_schema)
        if mets_schema.validate(self.xml) == True:
            return "Valid"
        else:
            return "Invalid"
    
    def listReferencedFiles(self):

        """Extracts a list of relative paths referenced in the <fileSec> section of the METS file."""
        self.list_of_referenced_files = []
        for file in self.xml.xpath("/mets:mets/mets:fileSec//mets:file/mets:FLocat", 
                                   namespaces={"mets": "http://www.loc.gov/METS/"}):
            self.list_of_referenced_files.append(file.xpath("@xlink:href", 
                                    namespaces={"xlink": "http://www.w3.org/1999/xlink"})[0])
            
    def listPackageFiles(self):

        """Returns a list of relative paths to every file located in the same folder as the METS file."""
        self.list_of_package_files = []
        for file in glob.glob(self.directory + '**/*', recursive=True):
            if not path.isdir(file) and not path.basename(file) == self.name:
                self.list_of_package_files.append(path.basename(file))

    def checkCompleteness(self):

        """Checks all referenced files in the mets:fileSec are present."""
        missing_files = []
        self.listReferencedFiles()
        for file in self.list_of_referenced_files:
            absolute_path_to_data_object = path.join(self.directory, file)
            if not path.exists(absolute_path_to_data_object):
                missing_files.append(file)
        if missing_files:
            return f"Incomplete. Files {missing_files} are missing."
        else:
            return f"Complete."
        
    def checkCompletenessAndFixity(self):

        """Checks all referenced files in the mets:fileSec are present and unaltered."""
        missing_files = []
        unchecked_files = []
        altered_files = []
        for file in self.xml.xpath("/mets:mets/mets:fileSec//mets:file/mets:FLocat", 
                                   namespaces={"mets": "http://www.loc.gov/METS/"}):
            relative_path_to_data_object = file.xpath("@xlink:href", 
                                    namespaces={"xlink": "http://www.w3.org/1999/xlink"})[0]
            absolute_path_to_data_object = path.join(self.directory, relative_path_to_data_object)
            if not path.exists(absolute_path_to_data_object):
                missing_files.append(relative_path_to_data_object)
            elif file.xpath("../@CHECKSUM") and file.xpath("../@CHECKSUMTYPE"):
                BUF_SIZE = 65536
                if file.xpath("../@CHECKSUMTYPE")[0] == "MD5":
                    checksum = hashlib.md5()
                elif file.xpath("../@CHECKSUMTYPE")[0] == "SHA-1":
                    checksum = hashlib.sha1()
                elif file.xpath("../@CHECKSUMTYPE")[0] == "SHA-256":
                    checksum = hashlib.sha256()
                elif file.xpath("../@CHECKSUMTYPE")[0] == "SHA-384":
                    checksum = hashlib.sha384()
                elif file.xpath("../@CHECKSUMTYPE")[0] == "SHA-512":
                    checksum = hashlib.sha512()
                with open(absolute_path_to_data_object, "rb") as binaryFile:
                    while True:
                        data = binaryFile.read(BUF_SIZE)
                        if not data:
                            break
                        checksum.update(data)
                if checksum.hexdigest() != file.xpath("../@CHECKSUM")[0]:
                    altered_files.append(relative_path_to_data_object)
            else:
                unchecked_files.append(relative_path_to_data_object)
        if missing_files and not altered_files:
            return f"Incomplete. Files {missing_files} are missing."
        if not missing_files and altered_files:
            return f"Altered. Altered files: {altered_files}."
        if missing_files and altered_files:
            return (f"Incomplete and altered. Files {missing_files} are missing. "
                    f"Altered iles {altered_files}.")
        else:
            if not unchecked_files:
                return f"Unaltered."
            else:
                return (f"Valid, but the fixity of files {unchecked_files} "
                        f"could not be checked.")
        
    def checkOrphanness(self):

        """Checks the absence of unreferenced files in the Information Package,
        i.e., files that are in the same folder as the METS file but that are not referenced
        in its file section <fileSec>."""
        orphan_files = []
        if not hasattr(self, 'list_of_referenced_files'):
            self.listReferencedFiles()
        self.listPackageFiles()
        for file in self.list_of_package_files:
            if file not in self.list_of_referenced_files:
                orphan_files.append(file)
        if orphan_files:
            return f"Orphan files: {orphan_files}."
        else:
            return f"No orphan files."


if __name__ == "__main__":
    if len(sys.argv) > 1:
        for argument in sys.argv[1:]:
            if path.exists(argument):
                manifest = METSFile(path.abspath(argument))
                print("Manifest:", argument, "\n", manifest.validate(), "\n", manifest.checkCompleteness(),
                    "\n", manifest.checkOrphanness(), "\n")
            else:
                print(f"File {argument} cannot be found.")
    else:
        print("You have to provide at least one path to a METS manifest.")