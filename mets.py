#!/usr/bin/python3
# -*-coding:utf-8 -*

"""Module for batch validation of METS packages: XML validation, presence and
fixity of all referenced files, absence of unreferenced files)."""

from os import path
import glob
import sys
import hashlib

from lxml import etree
import importlib.resources
from tabulate import tabulate


METSschema_filename = "mets.xsd"
with importlib.resources.as_file(
    importlib.resources.files("schemas").joinpath(METSschema_filename)
) as METS_resource:
    parsed_schema = etree.parse(METS_resource)
    mets_schema = etree.XMLSchema(parsed_schema)


class METSPackage:

    """This class is instantiated for each XML-METS file. It contains methods
    used to check the consistency of the manifest with the Information
     package, i.e., the directory where the XML-METS file is located."""

    def __init__(self, path_to_mets_file) -> None:
        self.path_to_mets_file = path_to_mets_file
        self.directory = path.split(path_to_mets_file)[0]
        self.name = path.split(path_to_mets_file)[1]
        self.xml = None

    def __repr__(self) -> str:
        return (
            f"Manifest: {self.name} in package {self.directory}.\n"
            f"\tWell-formed: {self.is_wellformed}\n"
            f"\tValid: {self.is_valid}\n"
            f"\tComplete and unaltered: {self.is_complete_and_unaltered}\n"
            f"\tHas no orphan files: {self.has_no_orphan_files}\n"
        )

    @property
    def has_wellformed_manifest(self):
        """Parses the XML file and returns True if it is well-formed, False
        otherwise."""

        try:
            self.xml = etree.parse(self.path_to_mets_file)
        except etree.XMLSyntaxError:
            return False
        return True

    @property
    def has_valid_manifest(self):
        """Validates the METS file against its XSD schema."""
        if not self.has_wellformed_manifest:
            return False
        return mets_schema.validate(self.xml)

    def listReferencedFiles(self):
        """Returns a list of relative paths referenced in the <fileSec> section
        of the METS file."""
        if self.has_wellformed_manifest:
            self.list_of_referenced_files = []
            for file in self.xml.xpath(
                "/mets:mets/mets:fileSec//mets:file/" "mets:FLocat",
                namespaces={"mets": "http://www.loc.gov/" "METS/"},
            ):
                self.list_of_referenced_files.append(
                    file.xpath(
                        "@xlink:href",
                        namespaces={"xlink": "http://www.w3.org/" "1999/xlink"},
                    )[0]
                )
            return self.list_of_referenced_files
        else:
            return None

    def listPackageFiles(self):
        """Returns a list of relative paths to every file located in the same
        folder as the METS file as the attribute list_of_package_files."""
        self.list_of_package_files = []
        for file in glob.glob(self.directory + "**/*", recursive=True):
            if not path.isdir(file) and not path.basename(file) == self.name:
                self.list_of_package_files.append(path.basename(file))

    @property
    def is_complete(self):
        """Checks referenced files in the mets:fileSec are present in
        the Information Package. Returns False and breaks at first missing
        file."""
        list_of_referenced_files = self.listReferencedFiles()
        if type(list_of_referenced_files) == list:
            for file in list_of_referenced_files:
                absolute_path_to_data_object = path.join(self.directory, file)
                if not path.exists(absolute_path_to_data_object):
                    return False
            return True
        else:
            return False

    def listMissingFiles(self):
        """Lists all files referenced in the METS <fileSec> that cannot be
        found at the expected location."""
        self.missing_files = []
        if self.listReferencedFiles():
            for file in self.list_of_referenced_files:
                absolute_path_to_data_object = path.join(self.directory, file)
                if not path.exists(absolute_path_to_data_object):
                    self.missing_files.append(file)
            return self.missing_files
        else:
            return None
                
    @property
    def is_unaltered(self):
        """Checks that referenced files in the mets:fileSec that
        can be found at their expected location are unaltered (may return True 
        even if there are missing files)."""
        if self.has_wellformed_manifest:
            for file in self.xml.xpath(
                "/mets:mets/mets:fileSec//mets:file/" "mets:FLocat",
                namespaces={"mets": "http://www.loc.gov/" "METS/"},
            ):
                relative_path_to_data_object = file.xpath(
                    "@xlink:href",
                    namespaces={"xlink": "http://www.w3.org/" "1999/xlink"},
                )[0]
                absolute_path_to_data_object = path.join(
                    self.directory, relative_path_to_data_object
                )
                if not path.exists(absolute_path_to_data_object):
                    pass
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
                        return False
                else:
                    return False
            return True
        else:
            return False
        
    def listAlteredFiles(self):
        """Returns a tuple whose first item is a list of altered files and the 
        second a list of unchecked files."""
        self.unchecked_files = []
        self.altered_files = []
        if self.has_wellformed_manifest:
            for file in self.xml.xpath(
                "/mets:mets/mets:fileSec//mets:file/" "mets:FLocat",
                namespaces={"mets": "http://www.loc.gov/" "METS/"},
            ):
                relative_path_to_data_object = file.xpath(
                    "@xlink:href",
                    namespaces={"xlink": "http://www.w3.org/" "1999/xlink"},
                )[0]
                absolute_path_to_data_object = path.join(
                    self.directory, relative_path_to_data_object
                )
                if not path.exists(absolute_path_to_data_object):
                    pass
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
                        self.altered_files.append(relative_path_to_data_object)
                else:
                    self.unchecked_files.append(relative_path_to_data_object)
            return (self.altered_files, self.unchecked_files)
        else:
            return (None, None)
        
    @property
    def has_no_orphan_files(self):
        """Checks the absence of unreferenced files in the Information Package,
        i.e., files that are in the same folder as the METS file but that are
        not referenced in its file section <fileSec>."""
        if self.has_wellformed_manifest:
            if not hasattr(self, "list_of_referenced_files"):
                self.listReferencedFiles()
            self.listPackageFiles()
            for file in self.list_of_package_files:
                if file not in self.list_of_referenced_files:
                    return False
            return True
        else:
            return False

    def listOrphanFiles(self):
        """Lists unreferenced files located in the Information Package, i.e.,
        files that are in the same folder as the METS file but that are not
        referenced in its file section <fileSec>."""
        self.orphan_files = ''
        if self.has_wellformed_manifest:
            if not hasattr(self, "list_of_referenced_files"):
                self.listReferencedFiles()
            self.listPackageFiles()
            for file in self.list_of_package_files:
                if file not in self.list_of_referenced_files:
                    self.orphan_files.append(file)
            return self.orphan_files
        else:
            return None

if __name__ == "__main__":
    if len(sys.argv) > 1:
        result_table = []
        for argument in sys.argv[1:]:
            if path.exists(argument):
                package = METSPackage(path.abspath(argument))
                has_wellformed_manifest = package.has_wellformed_manifest
                has_valid_manifest = package.has_valid_manifest
                is_complete = package.is_complete
                missing_files = ''
                if not is_complete:
                    missing_files = package.listMissingFiles()
                is_unaltered = package.is_unaltered
                altered_and_unchecked_files = (None, None)
                if not is_unaltered:
                    altered_and_unchecked_files = package.listAlteredFiles()
                has_no_orphan_files = package.has_no_orphan_files
                orphan_files = ''
                if not has_no_orphan_files:
                    orphan_files = package.listOrphanFiles()

                result_table.append(
                    [
                        argument,
                        has_wellformed_manifest,
                        has_valid_manifest,
                        is_complete,
                        missing_files,
                        is_unaltered,
                        altered_and_unchecked_files[0],
                        altered_and_unchecked_files[1],
                        has_no_orphan_files,
                        orphan_files
                    ]
                )
            else:
                print(f"File {argument} cannot be found.")
        print(
            tabulate(
                result_table,
                headers=[
                    "METS file",
                    "Well-formed",
                    "Valid",
                    "Complete",
                    "Missing files",
                    'Unaltered',
                    "Altered files",
                    "Unchecked files",
                    "Has no orphan files",
                    "Orphan files"
                ]
            )
        )
    else:
        print("You have to provide at least one path to a METS manifest.")
