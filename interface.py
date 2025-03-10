#!/usr/bin/python3
# -*-coding:utf-8 -*

"""GUI module for METS validation & integrity checking."""

from os import path
from time import strftime, localtime
from math import floor
import csv

import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter.messagebox import showinfo, showerror
import importlib.resources
import tkfilebrowser

import mets


class UndefinedInformationPackages(Exception):
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


mets_pattern = r""


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
            f"Analysis report "
            f'performing {", ".join(action for action in self.actions)}, '
            f'started at {strftime("%Y-%m-%dT%H:%M:%S%z", self.date)}.'
        )


class App(tk.Tk):
    def __init__(self):
        super().__init__()

        # Interface creation
        self.title("METS packages validation")
        self.geometry("1900x650")
        with importlib.resources.as_file(
            importlib.resources.files("mets_icon").joinpath("mets.png")
        ) as METS_icon:
            self.icon = tk.PhotoImage(file=METS_icon)
            self.iconphoto(True, self.icon)

        # Label to introduce the METS filename pattern entry.
        self.define_metspattern_label = ttk.Label(
            self, text="1. Enter the METS REGEX filename pattern:"
        )
        self.define_metspattern_label.grid(row=0, column=0, sticky=tk.W)

        # Entry for defining the METS filename pattern.
        self.mets_pattern = tk.StringVar()
        self.define_metspattern_entry = ttk.Entry(self, textvariable=self.mets_pattern)
        self.mets_pattern.set("manifest.xml")
        self.define_metspattern_entry.grid(row=0, column=1)

        # Label to introduce the IP type selection.
        self.IPtype_label = ttk.Label(
            self, text="2. Select the Information Package type:"
        )
        self.IPtype_label.grid(row=1, column=0, sticky=tk.W)

        # Radiobuttons to define the IP type.
        self.selected_package_type = tk.StringVar()
        self.directory_package_type_radiobutton = ttk.Radiobutton(
            self,
            text="Directory",
            value="directory",
            variable=self.selected_package_type,
        )
        self.container_package_type_radiobutton = ttk.Radiobutton(
            self,
            text="ZIP/TAR container file",
            value="container",
            variable=self.selected_package_type,
        )
        self.directory_package_type_radiobutton.grid(row=1, column=1)
        self.container_package_type_radiobutton.grid(row=2, column=1)
        self.selected_package_type.set("directory")

        # Button to select the directory where METS Information Packages are located.
        self.define_directory_button = ttk.Button(
            self, text="3. Select / add IPs for analysis", command=self.define_IPs
        )
        self.define_directory_button.grid(row=3, column=0, sticky=tk.W)
        self.define_directory_button.focus()

        # Label to introduce the actions selection.
        self.actions_label = ttk.Label(self, text="4. Select one or more actions.")
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
            text=("Check if the packages contain unreferenced files"),
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
            text="5. Launch the test",
        )
        self.launch_analysis_button.grid(row=9, column=0)
        # Set the table frame for displaying the analysis results.
        self.report_table_frame = tk.Frame(self, width=1800)
        self.report_table_frame.grid(columnspan=2, row=10)
        # Display scrollbar for the report diplay table
        self.table_vertical_scroll = ttk.Scrollbar(self.report_table_frame)
        self.table_vertical_scroll.grid(column=1, row=0, sticky=tk.NS)
        # Display the report in a table in the interface.
        self.display_report_table = ttk.Treeview(
            self.report_table_frame,
            show="headings",
            height=12,
            yscrollcommand=self.table_vertical_scroll.set,
        )
        self.table_vertical_scroll.configure(command=self.display_report_table.yview)
        self.display_report_table["columns"] = (
            "package",
            "wf_check",
            "validation",
            "completeness_check",
            "missing_files",
            "fixity_check",
            "altered_files",
            "unchecked_files",
            "orphanness_check",
            "orphan_files",
        )
        self.display_report_table.column("#0", stretch=tk.NO)
        self.display_report_table.column("package", anchor=tk.W, width=500)
        self.display_report_table.column("wf_check", anchor=tk.W, width=150)
        self.display_report_table.column("validation", anchor=tk.W, width=60)
        self.display_report_table.column("completeness_check", anchor=tk.W, width=110)
        self.display_report_table.column("missing_files", anchor=tk.W, width=210)
        self.display_report_table.column("fixity_check", anchor=tk.W, width=110)
        self.display_report_table.column("altered_files", anchor=tk.W, width=200)
        self.display_report_table.column("unchecked_files", anchor=tk.W, width=200)
        self.display_report_table.column("orphanness_check", anchor=tk.W, width=115)
        self.display_report_table.column("orphan_files", anchor=tk.W, width=200)

        self.display_report_table.heading("#0", text="", anchor=tk.W)
        self.display_report_table.heading("package", text="Package", anchor=tk.W)
        self.display_report_table.heading("wf_check", text="Well-formed", anchor=tk.W)
        self.display_report_table.heading("validation", text="Valid", anchor=tk.W)
        self.display_report_table.heading(
            "completeness_check", text="Complete", anchor=tk.W
        )
        self.display_report_table.heading(
            "missing_files", text="Missing files", anchor=tk.W
        )
        self.display_report_table.heading("fixity_check", text="Unaltered", anchor=tk.W)
        self.display_report_table.heading(
            "altered_files", text="Altered files", anchor=tk.W
        )
        self.display_report_table.heading(
            "unchecked_files", text="Unchecked files", anchor=tk.W
        )
        self.display_report_table.heading(
            "orphanness_check", text="No orphan", anchor=tk.W
        )
        self.display_report_table.heading(
            "orphan_files", text="Orphan files", anchor=tk.W
        )
        self.display_report_table.grid(column=0, row=1)
        # Button to clear the Information Packages list.
        self.define_directory_button = ttk.Button(
            self, text="Clear list of IPs", command=self.clear_IPs_list
        )
        self.define_directory_button.grid(row=9, column=1, sticky=tk.E)

    def define_IPs(self):
        """Asks the user to define Information Packages they want to analyze."""

        global IPs

        if self.selected_package_type.get() == "directory":
            new_list = tkfilebrowser.askopendirnames()

        elif self.selected_package_type.get() == "container":
            new_list = tkfilebrowser.askopenfilenames()

        try:
            IPs.extend(new_list)
        except NameError:
            IPs = list(new_list)

        self.display_report_table.delete(*self.display_report_table.get_children())
        index = 1
        for IP in IPs:
            self.display_report_table.insert(
                parent="", index="end", iid=index, text="", values=[IP]
            )
            index += 1
        self.display_report_table.grid(column=0, row=0)
        self.directory_package_type_radiobutton.configure(state="disabled")
        self.container_package_type_radiobutton.configure(state="disabled")

    def launch_test(
        self,
        validate_action,
        checkCompleteness_action,
        checkFixity_action,
        checkOrphanness_action,
    ):
        """Calls the selected functions to perform tests selected by the user"""

        global IPs, mets_pattern

        # Exceptions if directory and METS file name pattern are not defined.
        if not IPs:
            raise UndefinedInformationPackages(
                "Please define at least one Information Package to analyse."
            )
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
            list_of_packages = {}
            for IP in IPs:
                list_of_packages[IP] = mets.METSPackage(
                    IP, mets_pattern)
            # Display progress bar
            progressBar = ttk.Progressbar(
                self, orient="horizontal", mode="determinate", length=280
            )
            progressBar.grid(row=11, columnspan=2)
            progress_label = ttk.Label(self, text=f"Current progress: 0%")
            progress_percentage = float()
            progress_label.grid(row=12, columnspan=2)
            # Initiate report
            report = Report(
                validate_action,
                checkCompleteness_action,
                checkFixity_action,
                checkOrphanness_action,
            )
            # Counter to evaluate progression of te analysis process
            counter = 0
            for manifest_path, package in list_of_packages.items():
                report.list_of_packages[manifest_path] = package
                # Well-formedness check
                report.wellformedness_report[manifest_path] = (
                    package.has_wellformed_manifest
                )
                # Validation check
                if validate_action.get() == "1":
                    report.validation_report[manifest_path] = package.has_valid_manifest
                # Completeness check
                if checkCompleteness_action.get() == "1":
                    report.completeness_report[manifest_path] = [package.is_complete]
                    if report.completeness_report[manifest_path][0] == False:
                        report.completeness_report[manifest_path].append(
                            package.listMissingFiles()
                        )
                # Fixity check
                if checkFixity_action.get() == "1":
                    report.fixity_report[manifest_path] = [package.is_unaltered]
                    if report.fixity_report[manifest_path][0] == False:
                        report.fixity_report[manifest_path].append(
                            package.listAlteredFiles()
                        )
                # Orphanness check
                if checkOrphanness_action.get() == "1":
                    report.orphanness_report[manifest_path] = [
                        package.has_no_orphan_files
                    ]
                    if report.orphanness_report[manifest_path][0] == False:
                        report.orphanness_report[manifest_path].append(
                            package.listOrphanFiles()
                        )
                counter += 1
                progress_percentage = round(counter / (len(list_of_packages) / 100), 2)
                progressBar.config(value=floor(progress_percentage))
                progress_label.config(
                    text=f"Current progress = {progress_percentage}%."
                )
                self.update_idletasks()
            # Generate report
            report = self.build_report(report)
            # Display button to define the location where report will be saved.
            select_output_location_button = ttk.Button(
                self,
                text="5. Select the location for the report file.",
                command=lambda: self.save_report(report),
            )
            select_output_location_button.grid(columnspan=2, row=13)
            # Filling the report table.
            self.display_report_table.delete(*self.display_report_table.get_children())
            index = 1
            for row in report.table[1:]:
                self.display_report_table.insert(
                    parent="", index="end", iid=index, text="", values=row
                )
                index += 1
            self.display_report_table.grid(column=0, row=0)
            # Message box to inform that the process ended.
            showinfo(
                "Process ended.",
                f"The process analyzed {len(list_of_packages)} packages.",
            )

    def build_report(self, report):
        report.table = []
        report.table.append(
            [
                "Package",
                "Well-formed",
                "Valid",
                "Complete",
                "Missing files",
                "Unaltered",
                "Altered files",
                "Unchecked files",
                "No orphan",
                "Orphan files",
            ]
        )
        for manifest_path in report.list_of_packages:
            row = [
                manifest_path,
                report.wellformedness_report[manifest_path],
            ]
            if "Validation" in report.columns:
                row.append(report.validation_report[manifest_path])
            else:
                row.append("Not performed")
            if "Completeness check" in report.columns:
                row.append(report.completeness_report[manifest_path][0])
                if len(report.completeness_report[manifest_path]) > 1:
                    row.append(report.completeness_report[manifest_path][1])
                else:
                    row.append("")
            else:
                row.append("Not performed")
                row.append("")
            if "Fixity check" in report.columns:
                row.append(report.fixity_report[manifest_path][0])
                if len(report.fixity_report[manifest_path]) > 1:
                    row.append(report.fixity_report[manifest_path][1][0])
                    row.append(report.fixity_report[manifest_path][1][1])
                else:
                    row.append("")
                    row.append("")
            else:
                row.append("Not performed")
                row.append("")
                row.append("")
            if "Orphanness check" in report.columns:
                row.append(report.orphanness_report[manifest_path][0])
                if len(report.orphanness_report[manifest_path]) > 1:
                    row.append(report.orphanness_report[manifest_path][1])
                else:
                    row.append("")
            else:
                row.append("Not performed")
                row.append("")
            report.table.append(row)
        return report

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
            for row in report.table:
                csvwriter.writerow(row)

        showinfo("Success!", f"Report saved at {location}.")

    def clear_IPs_list(self):

        global IPs

        IPs = []
        self.display_report_table.delete(*self.display_report_table.get_children())
        self.directory_package_type_radiobutton.configure(state="normal")
        self.container_package_type_radiobutton.configure(state="normal")

    # def report_callback_exception(self, exc, val, tb):
        # """Manages exceptions and returns them to the user in an error box"""
        # showerror("Error", message=str(val))


if __name__ == "__main__":
    root = App()
    root.mainloop()
