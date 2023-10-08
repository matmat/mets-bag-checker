"""Module of the GUI for METS validation & integrity checking."""

#!/usr/bin/python3.10
# -*-coding:utf-8 -*


from os import path
from time import localtime,strftime
from math import floor
import csv

import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter.messagebox import showinfo

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

class Report():

    """This class is intended for analysis reports"""

    def __init__(self, validate_action, checkCompleteness_action, checkFixity_action, checkOrphanness_action) -> None:
        self.actions = []
        self.date = localtime()
        if validate_action.get() == '1':
            self.validation_report = {}
            self.actions.append('Validation')
        if checkCompleteness_action.get() == '1'  and (not checkFixity_action.get() or checkFixity_action.get() == '0'):
            self.completeness_report = {}
            self.actions.append('Completeness check')
        if checkFixity_action.get() == '1':
            self.completenessAndFixity_report = {}
            self.actions.append('Completeness and fixity check')
        if checkOrphanness_action.get() == '1':
            self.orphanness_report = {}
            self.actions.append('Orphanness check')
    
    def __repr__(self) -> str:
        return (f'Analysis report of the folder {mets.directory} '
                f'performing {", ".join(action for action in self.actions)}, '
                f'started at {strftime("%Y-%m-%dT%H:%M:%S%z", self.date)}.')

def define_directory():

    """Asks the user to define the directory where the Information Packages are located."""

    mets.directory = filedialog.askdirectory()
    directory_label.config(text=mets.directory)

def launch_test(validate_action, checkCompleteness_action, checkFixity_action, checkOrphanness_action):

    """Calls the selected functions to perform tests selected by the user"""

    # Exceptions if directory and METS file name pattern are not defined.
    if mets.directory == '':
        raise UndefinedDirectory('Please define a folder to analyse.')
    elif mets_pattern.get() == '':
        raise UndefinedMETSPattern('Please define the METS files name pattern.')
    elif validate_action.get() != '1' and checkCompleteness_action.get() != '1' and \
        checkFixity_action.get() != '1' and checkOrphanness_action.get() != '1':
        raise UndefinedAction('No action is selected.')
    else:
        # Detection of the Information Packages based on the METS file name pattern. 
        mets.mets_pattern = '/**/' + mets_pattern.get()
        IPs = mets.InformationPackages()
        IPs.find_information_packages()
        # Display progress bar
        progressBar = ttk.Progressbar(frame1, orient='horizontal', mode='determinate', length=280)
        progressBar.grid(row=8, column=0)
        progress_label = ttk.Label(frame1, text=f"Current progress: 0%")
        progress_percentage = float()
        progress_label.grid(row=9, column=0)
        # # Display abort button
        # abortButton = ttk.Button(frame1, text='Abort analysis')
        # abortButton.grid(row=10, column=0)
        # Initiate report
        report = Report(validate_action, checkCompleteness_action, checkFixity_action, checkOrphanness_action)
        # Counter to evaluate progression of the analysis process
        counter = 0
        for file in IPs.list_of_ips:
            manifest = mets.METSFile(path.join(file[0], file[1]))
            # Validation check
            if validate_action.get() == '1':
                report.validation_report[manifest.path_to_mets_file] = manifest.validate()
            # Completeness check alone
            if checkCompleteness_action.get() == '1' and (not checkFixity_action.get() or checkFixity_action.get() == '0'):
                report.completeness_report[manifest.path_to_mets_file] = manifest.checkCompleteness()
            # Completeness check plus fixity check
            if checkFixity_action.get() == '1':
                report.completenessAndFixity_report[manifest.path_to_mets_file] = manifest.checkCompletenessAndFixity()
            # Orphanness check
            if checkOrphanness_action.get() == '1':
                report.orphanness_report[manifest.path_to_mets_file] = manifest.checkOrphanness()
            counter += 1
            progress_percentage = round(counter / (len(IPs.list_of_ips) / 100), 2)
            progressBar.config(value=floor(progress_percentage))
            progress_label.config(text=f'Current progress = {progress_percentage}%.')
            frame1.update_idletasks()
            select_output_location_button = ttk.Button(frame1, text="Select the location for the report file.", command=lambda:save_report(report, IPs))
            select_output_location_button.grid(column=0, row=10)
        showinfo("Process ended.", f"The process analyzed {len(IPs.list_of_ips)} packages.")

def save_report(report, IPs):
    location = filedialog.asksaveasfilename(initialdir=path.curdir,
                                            initialfile=f'Report_{strftime("%Y-%m-%dT%H:%M:%S%z", report.date)}.csv',
                                            title = "Select the report location.",
                                            filetypes = [("csv files", "*.csv")])
    with open(location, 'w', newline='') as csvreport:
        csvwriter = csv.writer(csvreport, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        report.actions.insert(0, 'Package')
        csvwriter.writerow(report.actions)
        for IP in IPs.list_of_ips:
            row = [IP[0]]
            if 'Validation' in report.actions:
                row.append(report.validation_report["/".join(IP)])
            if 'Completeness check' in report.actions:
                row.append(report.completeness_report["/".join(IP)])
            if 'Completeness and fixity check' in report.actions:
                row.append(report.completenessAndFixity_report["/".join(IP)])
            if 'Orphanness check' in report.actions:
                row.append(report.orphanness_report["/".join(IP)])
            csvwriter.writerow(row)


# Interface creation
root = tk.Tk()
root.title("METS packages validation")
root.geometry('1500x1000')
icon = tk.PhotoImage(file='mets.png')
root.iconphoto(True, icon)

# Main frame creation
frame1 = tk.Frame(root, width=700, height=400)
frame1.pack()
frame1.columnconfigure(0, weight=1)
frame1.columnconfigure(1, weight=1)

# Button to select the directory where METS Information Packages are located.
define_directory_button = ttk.Button(frame1, text="Select a folder for analysis",
                                     command=define_directory)
define_directory_button.grid(row=0, column=0)
define_directory_button.focus()

# Label displaying the chosen directory.
directory_label = ttk.Label(frame1)
directory_label.grid(row=0, column=1)

# Label to introduce the METSfilename pattern entry.
define_metspattern_label = ttk.Label(frame1,
                                     text="Enter the METS filename or pattern (wildcards are accepted):")
define_metspattern_label.grid(row=1, column=0)

# Entry for defining the METS filename pattern.
mets_pattern = tk.StringVar()
define_metspattern_entry = ttk.Entry(frame1, textvariable=mets_pattern)
mets_pattern.set('manifest.xml')
define_metspattern_entry.grid(row=1, column=1)

# Checkboxes to select which operations to perform.
validate_action = tk.StringVar()
checkCompleteness_action = tk.StringVar()
checkFixity_action = tk.StringVar()
checkOrphanness_action = tk.StringVar()
checkbox_operation_validate = ttk.Checkbutton(frame1, text="Validate METS manifests",
                                              variable=validate_action)
checkbox_operation_checkCompleteness = ttk.Checkbutton(frame1,
                                                       text="Check all referenced files are present",
                                                        variable=checkCompleteness_action)
checkbox_operation_checkFixity = ttk.Checkbutton(frame1, text="Check all referenced files' fixity",
                                                 variable=checkFixity_action)
checkbox_operation_checkOrphanness = ttk.Checkbutton(frame1,
                                                     text=("Check if the packages "
                                                           "contain unreferenced files"),
                                                            variable=checkOrphanness_action)
checkbox_operation_validate.grid(row=2, column=0, sticky=tk.W)
checkbox_operation_checkCompleteness.grid(row=3, column=0, sticky=tk.W)
checkbox_operation_checkFixity.grid(row=4, column=0, sticky=tk.W)
checkbox_operation_checkOrphanness.grid(row=5, column=0, sticky=tk.W)

# Button for launching the analysis.
launch_analysis_button = ttk.Button(frame1, command=lambda: launch_test(validate_action,
                                                                        checkCompleteness_action,
                                                                        checkFixity_action,
                                                                        checkOrphanness_action),
                                                                        text="Launch the test")
launch_analysis_button.grid(row=6, column=0)

# Additional code to correct blurry edges on Windows.
# try:
#     from ctypes import windll

#     windll.shcore.SetProcessDpiAwareness(1)
# finally:
root.mainloop()
