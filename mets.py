#!/usr/bin/python3
# -*-coding:utf-8 -*

"""Module for batch validation of METS packages: XML validation, presence and
fixity of all referenced files, absence of unreferenced files)."""

from os import path
import glob
import sys
import hashlib

import zipfile
from io import BytesIO
from lxml import etree
import importlib.resources


class NotAZipError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class ManifestNotFoundError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


METSschema_filename = "mets.xsd"
with importlib.resources.as_file(
    importlib.resources.files("schemas").joinpath(METSschema_filename)
) as METS_resource:
    parsed_schema = etree.parse(METS_resource)
    mets_schema = etree.XMLSchema(parsed_schema)


class METSPackage:
    """This class is instantiated for each METS package. It contains methods
    used to check the consistency of the manifest with the Information
     package, i.e., the directory or ZIP file where the XML-METS file is located."""

    def __init__(self, package, manifest_name, package_type="directory") -> None:
        self.package = package
        if package_type == "zip":
            if zipfile.is_zipfile(self.package):
                zip_package = zipfile.ZipFile(self.package)
                self.root_dir = zip_package.namelist()[0].split("/")[0]
                self.manifest_name = path.join(self.root_dir, manifest_name)
            else:
                raise NotAZipError(f"The package {self.package} is not a ZIP file.")
        elif package_type == "directory":
            self.manifest_name = manifest_name
        self.package_type = package_type
        self.xml = None

    def __repr__(self) -> str:
        return (
            f"Manifest: {self.manifest_name} in package {self.package}.\n"
            f"\tWell-formed: {self.has_wellformed_manifest}\n"
            f"\tValid: {self.has_valid_manifest}\n"
            f"\tComplete: {self.is_complete}\n"
            f"\tUnaltered: {self.is_unaltered}\n"
            f"\tHas no orphan files: {self.has_no_orphan_files}\n"
        )

    @property
    def has_wellformed_manifest(self):
        """Parses the XML file and returns True if it is well-formed, False
        otherwise."""

        try:
            if self.package_type == "directory":
                try:
                    self.xml = etree.parse(path.join(self.package, self.manifest_name))
                except OSError:
                    return False
            elif self.package_type == "zip":
                zip_file = zipfile.ZipFile(self.package)
                list_zip_content = zip_file.infolist()
                for file in list_zip_content:
                    if path.basename(file.filename) == path.basename(
                        self.manifest_name
                    ):
                        xml_file_content = zip_file.read(file)
                        self.xml = etree.fromstring(xml_file_content)
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
        self.list_of_referenced_files = []
        if self.has_wellformed_manifest:
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

    def listPackageFiles(self):
        """Returns a list of relative paths to every file located in the same
        folder as the METS file as the attribute list_of_package_files."""
        self.list_of_package_files = []
        if self.package_type == "directory":
            for file in glob.glob(path.join(self.package, "**/*"), recursive=True):
                if (
                    not path.isdir(file)
                    and not path.basename(file) == self.manifest_name
                ):
                    self.list_of_package_files.append(
                        path.relpath(file, start=self.package)
                    )
        elif self.package_type == "zip":
            zip_file = zipfile.ZipFile(self.package)
            list_zip_content = zip_file.infolist()
            for file in list_zip_content:
                if not file.is_dir():
                    file_name_from_root_directory = path.relpath(
                        file.filename, start=self.root_dir
                    )
                    if file_name_from_root_directory != path.basename(
                        self.manifest_name
                    ):
                        self.list_of_package_files.append(file_name_from_root_directory)
        return self.list_of_package_files

    @property
    def is_complete(self):
        """Checks referenced files in the mets:fileSec are present in
        the Information Package."""
        if self.has_wellformed_manifest:
            try:
                if not hasattr(self, "list_of_referenced_files"):
                    self.listReferencedFiles()
                if not hasattr(self, "list_of_package_files"):
                    self.listPackageFiles()
                if self.list_of_referenced_files:
                    for file in self.list_of_referenced_files:
                        if file not in self.list_of_package_files:
                            return False
                    return True
                else:
                    return True
            except TypeError:
                return False
        else:
            return False

    def listMissingFiles(self):
        """Lists all files referenced in the METS <fileSec> that cannot be
        found at the expected location."""
        self.missing_files = []
        if not hasattr(self, "list_of_referenced_files"):
            self.listReferencedFiles()
        if not hasattr(self, "list_of_package_files"):
            self.listPackageFiles()
        if self.list_of_referenced_files:
            for file in self.list_of_referenced_files:
                if file not in self.list_of_package_files:
                    self.missing_files.append(file)
        return self.missing_files

    @property
    def is_unaltered(self):
        """Checks that referenced files in the mets:fileSec that
        can be found at their expected location are unaltered (may return True
        even if there are missing files)."""

        if self.has_wellformed_manifest:
            if not hasattr(self, "list_of_package_files"):
                self.listPackageFiles()
            if self.package_type == "zip":
                zip_file = zipfile.ZipFile(self.package)
            for file in self.xml.xpath(
                "/mets:mets/mets:fileSec//mets:file/" "mets:FLocat",
                namespaces={"mets": "http://www.loc.gov/" "METS/"},
            ):
                relative_path_to_file = file.xpath(
                    "@xlink:href",
                    namespaces={"xlink": "http://www.w3.org/" "1999/xlink"},
                )[0]
                if relative_path_to_file not in self.list_of_package_files:
                    pass
                elif file.xpath("../@CHECKSUM") and file.xpath("../@CHECKSUMTYPE"):
                    buffer_size = 65536
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
                    if self.package_type == "directory":
                        with open(
                            path.join(self.package, relative_path_to_file), "rb"
                        ) as binaryFile:
                            while True:
                                data = binaryFile.read(buffer_size)
                                if not data:
                                    break
                                checksum.update(data)
                    elif self.package_type == "zip":
                        with zip_file.open(
                            path.join(self.root_dir, relative_path_to_file)
                        ) as zip_entry:
                            while True:
                                data = zip_entry.read(buffer_size)
                                chunk_stream = BytesIO(data)
                                chunk_bytes = chunk_stream.read()
                                if not data:
                                    break
                                checksum.update(chunk_bytes)
                    if checksum.hexdigest() != file.xpath("../@CHECKSUM")[0]:
                        if self.package_type == "zip":
                            zip_file.close()
                        return False
                else:
                    if self.package_type == "zip":
                        zip_file.close()
                    return False
            if self.package_type == "zip":
                zip_file.close()
            return True
        else:
            return False

    def listAlteredFiles(self):
        """Returns a tuple whose first item is a list of altered files and the
        second a list of unchecked files."""
        self.unchecked_files = []
        self.altered_files = []
        if self.has_wellformed_manifest:
            if not hasattr(self, "list_of_package_files"):
                self.listPackageFiles()
            if self.package_type == "zip":
                zip_file = zipfile.ZipFile(self.package)
            for file in self.xml.xpath(
                "/mets:mets/mets:fileSec//mets:file/" "mets:FLocat",
                namespaces={"mets": "http://www.loc.gov/" "METS/"},
            ):
                relative_path_to_file = file.xpath(
                    "@xlink:href",
                    namespaces={"xlink": "http://www.w3.org/" "1999/xlink"},
                )[0]
                if relative_path_to_file not in self.list_of_package_files:
                    pass
                elif file.xpath("../@CHECKSUM") and file.xpath("../@CHECKSUMTYPE"):
                    buffer_size = 65536
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

                    if self.package_type == "directory":
                        with open(
                            path.join(self.package, relative_path_to_file), "rb"
                        ) as binaryFile:
                            while True:
                                data = binaryFile.read(buffer_size)
                                if not data:
                                    break
                                checksum.update(data)
                    elif self.package_type == "zip":
                        with zip_file.open(
                            path.join(self.root_dir, relative_path_to_file)
                        ) as zip_entry:
                            while True:
                                data = zip_entry.read(buffer_size)
                                chunk_stream = BytesIO(data)
                                chunk_bytes = chunk_stream.read()
                                if not data:
                                    break
                                checksum.update(chunk_bytes)
                    if checksum.hexdigest() != file.xpath("../@CHECKSUM")[0]:
                        if self.package_type == "zip":
                            relative_path_to_file = path.join(
                                self.root_dir, relative_path_to_file
                            )
                        self.altered_files.append(relative_path_to_file)
                else:
                    if self.package_type == "zip":
                        relative_path_to_file = path.join(
                            self.root_dir, relative_path_to_file
                        )
                    self.unchecked_files.append(relative_path_to_file)
        if self.package_type == "zip":
            zip_file.close()
        return (self.altered_files, self.unchecked_files)

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
        self.list_of_orphan_files = []
        if self.has_wellformed_manifest:
            if not hasattr(self, "list_of_referenced_files"):
                self.listReferencedFiles()
            self.listPackageFiles()
            for file in self.list_of_package_files:
                if file not in self.list_of_referenced_files:
                    self.list_of_orphan_files.append(file)
        return self.list_of_orphan_files


def check(package, manifest):
    if path.exists(package):
        if path.isdir(package):
            if path.exists(path.join(package, manifest)):
                package = METSPackage(package, manifest, package_type="directory")
                print(package)
            else:
                raise ManifestNotFoundError(
                    f"Manifest {manifest} cannot be found in package {package}."
                )
        elif zipfile.is_zipfile(package):
            try:
                zip_file = zipfile.ZipFile(package)
                zip_file.getinfo(
                    path.join(zip_file.namelist()[0].split("/")[0], manifest)
                )
                package = METSPackage(package, manifest, package_type="zip")
                print(package)
            except KeyError:
                print(f"Manifest {manifest} cannot be found in package {package}.")
        else:
            print("Argument #1 must be a path to a directory or to a ZIP file.")
    else:
        print(f"Package {package} cannot be found.")


if __name__ == "__main__":
    if len(sys.argv) == 3:
        check(sys.argv[1], sys.argv[2])
    else:
        print(
            "You have to provide one path to a METS package (directory or ZIP file) and the name of the manifest."
        )
