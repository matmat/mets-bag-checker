#!/usr/bin/python3
# -*-coding:utf-8 -*

"""Unit tests for the module mets.py."""

import unittest
from lxml import etree

import mets

class MetsTest(unittest.TestCase):
    
    """Test case for functions of the module mets"""

    def test_valid(self):
        
        """Tests that the function validate returns "valid" for a valid
        XML-METS file"""

        manifest = mets.METSFile("sampleMETSPackages/XMLValid/LOCmets.xml")
        self.assertEqual(manifest.validate(), "Valid")
    
    def test_invalid(self):
        
        """Tests that the function validate returns "Invalid" for an invalid
        XML-METS file"""

        manifest = mets.METSFile("sampleMETSPackages/XMLInvalid/"
                                 "filnumconsa_producerPackage_initialDelivery_example_version6.xml")
        self.assertEqual(manifest.validate(), "Invalid")

unittest.main()