#!/usr/bin/python3
# -*-coding:utf-8 -*

"""Unit tests for the module mets.py."""

import unittest
from lxml import etree
import importlib.resources

import mets


class MetsTest(unittest.TestCase):

    """Test case for functions of the module mets"""

    def test_is_wellformed(self):
        """Tests that the property has_wellformed_manifest returns True for a
        well-formed XML-METS file and False for an ill-formed one."""

        with importlib.resources.as_file(
            importlib.resources.files("sampleMETSPackages.XMLValid").joinpath(
                "LOCmets.xml"
            )
        ) as file:
            manifest = mets.METSPackage(file)
            self.assertEqual(manifest.has_wellformed_manifest, True)

    def test_is_valid(self):
        """Tests that the property has_valid_manifest returns True for a valid
        XML-METS file and False for an invalid one."""

        with importlib.resources.as_file(
            importlib.resources.files("sampleMETSPackages.XMLValid").joinpath(
                "LOCmets.xml"
            )
        ) as file:
            manifest = mets.METSPackage(file)
            self.assertEqual(manifest.has_valid_manifest, True)

        with importlib.resources.as_file(
            importlib.resources.files("sampleMETSPackages.XMLInvalid").joinpath(
                "filnumconsa_producerPackage_initialDelivery_example_version6.xml"
            )
        ) as file:
            manifest = mets.METSPackage(file)
            self.assertEqual(manifest.has_valid_manifest, False)

    def test_orphaned_files(self):
        """Tests that orphaned files are returned as a list"""
        with importlib.resources.as_file(
            importlib.resources.files("sampleMETSPackages.OrphanedFiles").joinpath(
                "LOCmets.xml"
            )
        ) as file:
            manifest = mets.METSPackage(file)
            self.assertEqual(manifest.has_no_orphan_files, False)
            self.assertEqual(manifest.listOrphanFiles(), ["orphan_file.txt"])

    def test_missing_files(self):
        """Tests that missing files are returned as a list"""
        with importlib.resources.as_file(
            importlib.resources.files("sampleMETSPackages.XMLValid").joinpath(
                "LOCmets.xml"
            )
        ) as file:
            manifest = mets.METSPackage(file)
            self.assertEqual(manifest.is_complete, False)
            self.assertEqual(len(manifest.listMissingFiles()), 3)


unittest.main()
