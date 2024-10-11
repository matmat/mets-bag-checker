#!/usr/bin/python3
# -*-coding:utf-8 -*

"""Module for batch validation of METS packages: XML validation, presence and
fixity of all referenced files, absence of unreferenced files)."""

from os import path
import glob
import sys
import hashlib
import re
import os

import zipfile
import tarfile
from io import BytesIO
from lxml import etree
import importlib.resources


class NotAContainerError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)

class ManifestNotFoundError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)

class ManifestReadingError(Exception):
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
     package, i.e., the directory or ZIP/TAR file where the XML-METS file is located."""

    def __init__(self, package, manifest_pattern) -> None:
        self.package = package
        if path.isfile(package):
            if zipfile.is_zipfile(self.package):
                self.package_type = "zip"
            elif tarfile.is_tarfile(self.package):
                self.package_type = "tar"
        elif path.isdir(package):
            self.package_type = "directory"        
        else:
            raise NotAContainerError(f"The package {self.package} is not a ZIP nor a TAR file.")
        self.manifest_pattern = manifest_pattern
        self.manifest_path = self.find_manifest()

    def __repr__(self) -> str:
        return (
            f"Manifest: {self.manifest_path} in package {self.package}.\n"
            f"\tWell-formed: {self.has_wellformed_manifest}\n"
            f"\tValid: {self.has_valid_manifest}\n"
            f"\tComplete: {self.is_complete}\n"
            f"\tUnaltered: {self.is_unaltered}\n"
            f"\tHas no orphan files: {self.has_no_orphan_files}\n"
        )

    def listPackageFiles(self):
        """Returns a list of relative paths to every file in the Package
        (including the manifest) as the attribute list_of_package_files."""
        self.list_of_package_files = []
        if self.package_type == "directory":
            tree = os.walk(self.package, topdown=True)
            for root, dirs, files in tree:
                for file in files:
                    if (not path.isdir(file)):
                        self.list_of_package_files.append(path.relpath(path.join(root, file), start=self.package))
        elif self.package_type == "zip":
            with zipfile.ZipFile(self.package) as zip_file:
                list_zip_content = zip_file.infolist()
                for file in list_zip_content:
                    if not file.is_dir():
                        self.list_of_package_files.append(file.filename)
        elif self.package_type == "tar":
            with tarfile.TarFile(self.package) as tar_file:
                list_tar_content = tar_file.getmembers()
                for file in list_tar_content:
                    if not file.isdir():
                        self.list_of_package_files.append(file.name)
        return self.list_of_package_files

    def find_manifest(self):
        self.list_of_package_files = self.listPackageFiles()
        try:
            for filepath in self.list_of_package_files:
                if re.search(self.manifest_pattern, filepath):
                    self.manifest_path = filepath
                    try:
                        if self.package_type == "directory":
                            manifest_xml = path.join(self.package, self.manifest_path)
                            self.xml = etree.parse(manifest_xml)
                        elif self.package_type == "zip":
                            with zipfile.ZipFile(self.package) as zip_file:
                                manifest_xml = zip_file.read(self.manifest_path)
                                self.xml = etree.fromstring(manifest_xml)
                        elif self.package_type == "tar":
                            with tarfile.TarFile(self.package) as tar_file:
                                xml_file_content = tar_file.extractfile(self.manifest_path)
                                manifest_xml = xml_file_content.read()
                                self.xml = etree.fromstring(manifest_xml)
                    except OSError:
                        raise ManifestReadingError("The manifest could not be parsed or is not well-formed.")
                    break
            return self.manifest_path
        except AttributeError:
            raise ManifestNotFoundError(f"No manifest with pattern {self.manifest_path} could be found in package {self.package}.")

    @property
    def has_wellformed_manifest(self):
        """Returns True if the manifest has been parsed successfully, False
        if not."""
        if hasattr(self, "xml"):
            return True
        else:
            return False

    @property
    def has_valid_manifest(self):
        """Validates the METS file against its XSD schema."""
        if not hasattr(self, "xml"):
            return False
        return mets_schema.validate(self.xml)

    def listReferencedFiles(self):
        """Returns a list of relative paths referenced in the <fileSec> section
        of the METS file."""
        self.list_of_referenced_files = []
        if hasattr(self, "xml"):
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

    @property
    def is_complete(self):
        """Checks referenced files in the mets:fileSec are present in
        the Information Package."""
        if hasattr(self, "xml"):
            try:
                if not hasattr(self, "list_of_referenced_files"):
                    self.listReferencedFiles()
                if self.list_of_referenced_files:
                    for file in self.list_of_referenced_files:
                        if path.join(path.split(self.manifest_path)[0], file) not in self.list_of_package_files:
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
        if self.list_of_referenced_files:
            for file in self.list_of_referenced_files:
                if path.join(path.split(self.manifest_path)[0], file) not in self.list_of_package_files:
                    self.missing_files.append(file)
        return self.missing_files

    @property
    def is_unaltered(self):
        """Checks that referenced files in the mets:fileSec that can be found 
        at their expected location are unaltered (may return True even if there 
        are missing files)."""

        if hasattr(self, "xml"):
            if self.package_type == "zip":
                zip_file = zipfile.ZipFile(self.package)
            elif self.package_type == "tar":
                tar_file = tarfile.TarFile(self.package)

            for file in self.xml.xpath(
                "/mets:mets/mets:fileSec//mets:file/" "mets:FLocat",
                namespaces={"mets": "http://www.loc.gov/" "METS/"},
            ):
                relative_path_to_file = file.xpath(
                    "@xlink:href",
                    namespaces={"xlink": "http://www.w3.org/" "1999/xlink"},
                )[0]
                if path.join(path.split(self.manifest_path)[0], relative_path_to_file) not in self.list_of_package_files:
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
                            path.join(self.package, path.split(self.manifest_path)[0], relative_path_to_file), "rb"
                        ) as binaryFile:
                            while True:
                                data = binaryFile.read(buffer_size)
                                if not data:
                                    break
                                checksum.update(data)
                    elif self.package_type == "zip":
                        with zip_file.open(
                            path.join(path.split(self.manifest_path)[0], relative_path_to_file)
                        ) as zip_entry:
                            while True:
                                data = zip_entry.read(buffer_size)
                                chunk_stream = BytesIO(data)
                                chunk_bytes = chunk_stream.read()
                                if not data:
                                    break
                                checksum.update(chunk_bytes)
                    elif self.package_type == "tar":
                        tar_entry = tar_file.getmember(
                        path.join(path.split(self.manifest_path)[0], relative_path_to_file))
                        file_entry = tar_file.extractfile(tar_entry)
                        while True:
                            data = file_entry.read(buffer_size)
                            chunk_stream = BytesIO(data)
                            chunk_bytes = chunk_stream.read()
                            if not data:
                                break
                            checksum.update(chunk_bytes)
                    if checksum.hexdigest() != file.xpath("../@CHECKSUM")[0]:
                        if self.package_type == "zip":
                            zip_file.close()
                        elif self.package_type == "tar":
                            tar_file.close()
                        return False
                else:
                    if self.package_type == "zip":
                        zip_file.close()
                    elif self.package_type == "tar":
                        tar_file.close()
                    return False
            if self.package_type == "zip":
                zip_file.close()
            elif self.package_type == "tar":
                tar_file.close()
            return True
        else:
            return False

    def listAlteredFiles(self):
        """Returns a tuple whose first item is a list of altered files and the
        second a list of unchecked files."""
        self.unchecked_files = []
        self.altered_files = []
        if hasattr(self, "xml"):
            if self.package_type == "zip":
                zip_file = zipfile.ZipFile(self.package)
            elif self.package_type == "tar":
                tar_file = tarfile.TarFile(self.package)
            for file in self.xml.xpath(
                "/mets:mets/mets:fileSec//mets:file/" "mets:FLocat",
                namespaces={"mets": "http://www.loc.gov/" "METS/"},
            ):
                relative_path_to_file = file.xpath(
                    "@xlink:href",
                    namespaces={"xlink": "http://www.w3.org/" "1999/xlink"},
                )[0]
                if path.join(path.split(self.manifest_path)[0], relative_path_to_file) not in self.list_of_package_files:
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
                            path.join(self.package, path.split(self.manifest_path)[0], relative_path_to_file), "rb"
                        ) as binaryFile:
                            while True:
                                data = binaryFile.read(buffer_size)
                                if not data:
                                    break
                                checksum.update(data)
                    elif self.package_type == "zip":
                        with zip_file.open(
                            path.join(path.split(self.manifest_path)[0], relative_path_to_file)
                        ) as zip_entry:
                            while True:
                                data = zip_entry.read(buffer_size)
                                chunk_stream = BytesIO(data)
                                chunk_bytes = chunk_stream.read()
                                if not data:
                                    break
                                checksum.update(chunk_bytes)
                    elif self.package_type == "tar":
                        tar_entry = tar_file.getmember(
                        path.join(path.split(self.manifest_path)[0], relative_path_to_file))
                        file_entry = tar_file.extractfile(tar_entry)
                        while True:
                            data = file_entry.read(buffer_size)
                            chunk_stream = BytesIO(data)
                            chunk_bytes = chunk_stream.read()
                            if not data:
                                break
                            checksum.update(chunk_bytes)
                    if checksum.hexdigest() != file.xpath("../@CHECKSUM")[0]:
                        self.altered_files.append(path.join(path.split(self.manifest_path)[0], relative_path_to_file))
                else:
                    self.unchecked_files.append(path.join(path.split(self.manifest_path)[0], relative_path_to_file))
        if self.package_type == "zip":
            zip_file.close()
        elif self.package_type == "tar":
            tar_file.close()
        return (self.altered_files, self.unchecked_files)

    @property
    def has_no_orphan_files(self):
        """Checks the absence of unreferenced files in the Information Package,
        i.e., files that are in the Package but that are not referenced in the 
        manifest's file section <fileSec>."""
        if hasattr(self, "xml"):
            if not hasattr(self, "list_of_referenced_files"):
                self.listReferencedFiles()
            for file in self.list_of_package_files:
                if path.relpath(file, start=path.split(self.manifest_path)[0]) \
                    not in self.list_of_referenced_files and file != \
                        self.manifest_path:
                    return False
            return True
        else:
            return False

    def listOrphanFiles(self):
        """Lists unreferenced files located in the Information Package, i.e.,
        files that are in the same folder as the METS file but that are not
        referenced in its file section <fileSec>."""
        self.list_of_orphan_files = []
        if hasattr(self, "xml"):
            if not hasattr(self, "list_of_referenced_files"):
                self.listReferencedFiles()
            for file in self.list_of_package_files:
                if path.relpath(file, start=path.split(self.manifest_path)[0]) \
                    not in self.list_of_referenced_files and file != \
                        self.manifest_path:
                    self.list_of_orphan_files.append(file)
        return self.list_of_orphan_files


def check(package, manifest):
    if path.exists(package):
        package = METSPackage(package, manifest)
        print(package)
    else:
        print(f"Package {package} cannot be found.")


if __name__ == "__main__":
    if len(sys.argv) == 3:
        check(sys.argv[1], sys.argv[2])
    else:
        print(
            "You have to provide one path to a METS package (directory or ZIP file) and the name of the manifest."
        )
