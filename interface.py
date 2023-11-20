#!/usr/bin/python3
# -*-coding:utf-8 -*

"""GUI module for METS validation & integrity checking."""

from os import path
from time import strftime, localtime
from math import floor
import glob
import csv

import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter.messagebox import showinfo
import importlib.resources

import mets


class UndefinedDirectory(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class UndefinedMETSPattern(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class UndefinedAction(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class UnparsableManifest(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


directory = ""
mets_pattern = r""


def find_information_packages(directory, mets_pattern):
    """Finds METS files in a defined directory based on their filename or
    filename pattern. Information packages are supposed to be the directories
    the detected METS file is in."""
    list_of_packages = {}
    for manifest_path in glob.glob(
        "./**/" + mets_pattern, root_dir=directory, recursive=True
    ):
        list_of_packages[manifest_path] = mets.METSPackage(
            path.join(directory, manifest_path)
        )
    return list_of_packages


class Report:

    """This class is intended for analysis reports"""

    def __init__(
        self,
        validate_action,
        checkCompleteness_action,
        checkFixity_action,
        checkOrphanness_action,
    ) -> None:
        self.list_of_packages = {}
        self.columns = ["Well-formedness check"]
        self.date = localtime()
        self.wellformedness_report = {}
        if validate_action.get() == "1":
            self.validation_report = {}
            self.columns.append("Validation")
        if checkCompleteness_action.get() == "1":
            self.completeness_report = {}
            self.columns.append("Completeness check")
            self.columns.append("Missing files")
        if checkFixity_action.get() == "1":
            self.fixity_report = {}
            self.columns.append("Fixity check")
            self.columns.append("Altered files")
            self.columns.append("Unchecked files")
        if checkOrphanness_action.get() == "1":
            self.orphanness_report = {}
            self.columns.append("Orphanness check")
            self.columns.append("Orphan files")

    def __repr__(self) -> str:
        return (
            f"Analysis report of the folder {directory} "
            f'performing {", ".join(action for action in self.actions)}, '
            f'started at {strftime("%Y-%m-%dT%H:%M:%S%z", self.date)}.'
        )


class App(tk.Tk):
    def __init__(self):
        super().__init__()

        # Interface creation
        self.title("METS packages validation")
        self.geometry("1000x400")
        with importlib.resources.as_file(
            importlib.resources.files("mets_icon").joinpath("mets.png")
        ) as METS_icon:
            self.icon = tk.PhotoImage(file=METS_icon)
            self.iconphoto(True, self.icon)

        # Button to select the directory where METS Information Packages are located.
        self.define_directory_button = ttk.Button(
            self, text="1. Select a folder for analysis", command=self.define_directory
        )
        self.define_directory_button.grid(row=0, column=0, sticky=tk.W)
        self.define_directory_button.focus()

        # Label displaying the chosen directory.
        self.directory_label = ttk.Label(self)
        self.directory_label.grid(row=0, column=1)

        # Label to introduce the METSfilename pattern entry.
        self.define_metspattern_label = ttk.Label(
            self, text="2. Enter the METS filename or pattern:"
        )
        self.define_metspattern_label.grid(row=2, column=0, sticky=tk.W)

        # Entry for defining the METS filename pattern.
        self.mets_pattern = tk.StringVar()
        self.define_metspattern_entry = ttk.Entry(self, textvariable=self.mets_pattern)
        self.mets_pattern.set("manifest.xml")
        self.define_metspattern_entry.grid(row=2, column=1)

        # Label to introduce the actions selection.
        self.actions_label = ttk.Label(self, text="3. Select one or more actions.")
        self.actions_label.grid(row=4, column=0, sticky=tk.W)
        # Checkboxes to select which operations to perform.
        self.validate_action = tk.StringVar()
        self.checkCompleteness_action = tk.StringVar()
        self.checkFixity_action = tk.StringVar()
        self.checkOrphanness_action = tk.StringVar()
        self.checkbox_operation_validate = ttk.Checkbutton(
            self, text="Validate METS manifests", variable=self.validate_action
        )
        self.checkbox_operation_checkCompleteness = ttk.Checkbutton(
            self,
            text="Check all referenced files are present",
            variable=self.checkCompleteness_action,
        )
        self.checkbox_operation_checkFixity = ttk.Checkbutton(
            self,
            text="Check all referenced files' fixity",
            variable=self.checkFixity_action,
        )
        self.checkbox_operation_checkOrphanness = ttk.Checkbutton(
            self,
            text=("Check if the packages " "contain unreferenced files"),
            variable=self.checkOrphanness_action,
        )
        self.checkbox_operation_validate.grid(row=5, column=0, sticky=tk.W)
        self.checkbox_operation_checkCompleteness.grid(row=6, column=0, sticky=tk.W)
        self.checkbox_operation_checkFixity.grid(row=7, column=0, sticky=tk.W)
        self.checkbox_operation_checkOrphanness.grid(row=8, column=0, sticky=tk.W)

        # Button for launching the analysis.
        self.launch_analysis_button = ttk.Button(
            self,
            command=lambda: self.launch_test(
                self.validate_action,
                self.checkCompleteness_action,
                self.checkFixity_action,
                self.checkOrphanness_action,
            ),
            text="4. Launch the test",
        )
        self.launch_analysis_button.grid(row=9, column=0)

    def define_directory(self):
        """Asks the user to define the directory where the Information Packages are located."""

        global directory

        directory = filedialog.askdirectory()
        self.directory_label.config(text=directory)

    def launch_test(
        self,
        validate_action,
        checkCompleteness_action,
        checkFixity_action,
        checkOrphanness_action,
    ):
        """Calls the selected functions to perform tests selected by the user"""

        global directory, mets_pattern

        # Exceptions if directory and METS file name pattern are not defined.
        if directory == "":
            raise UndefinedDirectory("Please define a folder to analyse.")
        elif self.mets_pattern.get() == "":
            raise UndefinedMETSPattern("Please define the METS files name pattern.")
        elif (
            validate_action.get() != "1"
            and checkCompleteness_action.get() != "1"
            and checkFixity_action.get() != "1"
            and checkOrphanness_action.get() != "1"
        ):
            raise UndefinedAction("Please select at least one action.")
        else:
            # Detection of the Information Packages based on the METS file namepattern.
            mets_pattern = self.mets_pattern.get()
            list_of_packages = find_information_packages(directory, mets_pattern)
            # Display progress bar
            progressBar = ttk.Progressbar(
                self, orient="horizontal", mode="determinate", length=280
            )
            progressBar.grid(row=10, column=0)
            progress_label = ttk.Label(self, text=f"Current progress: 0%")
            progress_percentage = float()
            progress_label.grid(row=11, column=0)
            # Initiate report
            report = Report(
                validate_action,
                checkCompleteness_action,
                checkFixity_action,
                checkOrphanness_action,
            )
            # Counter to evaluate progression of the analysis process
            counter = 0
            for manifest_relative_path, package in list_of_packages.items():
                report.list_of_packages[manifest_relative_path] = package
                # Well-formedness check
                report.wellformedness_report[
                    package.path_to_mets_file
                ] = package.has_wellformed_manifest
                # Validation check
                if validate_action.get() == "1":
                    report.validation_report[
                        package.path_to_mets_file
                    ] = package.has_valid_manifest
                # Completeness check
                if checkCompleteness_action.get() == "1":
                    report.completeness_report[package.path_to_mets_file] = [
                        package.is_complete
                        ]
                    if (
                        report.completeness_report[package.path_to_mets_file][0]
                        == False
                    ):
                        report.completeness_report[package.path_to_mets_file].append(
                            package.listMissingFiles()
                        )
                # Fixity check
                if checkFixity_action.get() == "1":
                    report.fixity_report[package.path_to_mets_file] = [
                        package.is_unaltered
                    ]
                    if report.fixity_report[package.path_to_mets_file][0] == False:
                        report.fixity_report[package.path_to_mets_file].append(
                            package.listAlteredFiles()
                        )
                # Orphanness check
                if checkOrphanness_action.get() == "1":
                    report.orphanness_report[package.path_to_mets_file] = [
                        package.has_no_orphan_files
                    ]
                    if report.orphanness_report[package.path_to_mets_file][0] == False:
                        report.orphanness_report[package.path_to_mets_file].append(
                            package.listOrphanFiles()
                        )
                counter += 1
                progress_percentage = round(counter / (len(list_of_packages) / 100), 2)
                progressBar.config(value=floor(progress_percentage))
                progress_label.config(
                    text=f"Current progress = {progress_percentage}%."
                )
                self.update_idletasks()
                select_output_location_button = ttk.Button(
                    self,
                    text="5. Select the location for the report file.",
                    command=lambda: self.save_report(report),
                )
                select_output_location_button.grid(column=0, row=12)
            showinfo(
                "Process ended.",
                f"The process analyzed {len(list_of_packages)} packages.",
            )

    def save_report(self, report):
        location = filedialog.asksaveasfilename(
            initialdir=path.curdir,
            initialfile=f'Report_{strftime("%Y-%m-%dT%H:%M:%S%z", report.date)}.csv',
            title="Select the report location.",
            filetypes=[("csv files", "*.csv")],
        )
        with open(location, "w", newline="") as csvreport:
            csvwriter = csv.writer(
                csvreport, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL
            )
            report.columns.insert(0, "Package")
            csvwriter.writerow(report.columns)
            for relative_path, package in report.list_of_packages.items():
                row = [
                    relative_path,
                    report.wellformedness_report[package.path_to_mets_file],
                ]
                if "Validation" in report.columns:
                    row.append(report.validation_report[package.path_to_mets_file])
                if "Completeness check" in report.columns:
                    row.append(report.completeness_report[package.path_to_mets_file][0])
                    if len(report.completeness_report[package.path_to_mets_file]) > 1:
                        row.append(report.completeness_report[package.path_to_mets_file][1])
                    else:
                        row.append('')
                if "Fixity check" in report.columns:
                    row.append(report.fixity_report[package.path_to_mets_file][0])
                    if len(report.fixity_report[package.path_to_mets_file]) > 1:
                        row.append(report.fixity_report[package.path_to_mets_file][1][0])
                        row.append(report.fixity_report[package.path_to_mets_file][1][1])
                    else:
                        row.append('')
                        row.append('')
                if "Orphanness check" in report.columns:
                    row.append(report.orphanness_report[package.path_to_mets_file][0])
                    if len(report.orphanness_report[package.path_to_mets_file]) > 1:
                        row.append(report.orphanness_report[package.path_to_mets_file][1])
                    else:
                        row.append('')
                csvwriter.writerow(row)

    # def report_callback_exception(self, exc, val, tb):

    #     """Manages exceptions and returns them to the user in an error box"""
    #     showerror("Error", message=str(val))


if __name__ == "__main__":
    root = App()
    root.mainloop()
