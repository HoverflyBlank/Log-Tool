
import PySimpleGUI as sg
from PySimpleGUI import SELECT_MODE_EXTENDED
import os
import subprocess
import threading
import time
import shutil
import mechanicalsoup
import re
import lzma

download_column = [
    [
        sg.Text("PI CONNECTION: [~~~~~~~~~~~~~~~]"),
        sg.Button("Get Logs", key="_GET LOGS BUTTON_", button_color=('white', 'red'))
    ],
    [
        sg.Text("Flight to download:")
    ],
    [
        sg.Listbox(values=[], size=(47, 20), key="_PI FILE LIST_")
    ],
    [
        sg.Text("Flight Name:"),
        sg.In(size=(23, 1), enable_events=True, key="_FLIGHT NAME_"),
        sg.Button("DOWNLOAD", key="_DOWNLOAD BUTTON_")
    ]
]

convert_column = [
    [
        sg.Text("Data Log Folder"),
        sg.In(size=(25, 1), enable_events=True, key="_FOLDER_"),
        sg.FolderBrowse()
    ],
    [
        sg.Text("Files to convert:")
    ],
    [
        sg.Listbox(values=[], select_mode=SELECT_MODE_EXTENDED, size=(47, 20), key="_FILE LIST_")
    ],
    [
        sg.Button("CONVERT", key="_CONVERT BUTTON_")
    ]
]

combine_column = [
    [
        sg.Text("Time Offset:"),
        sg.In(key="_TIME OFFSET_", tooltip="Set time offset if log times do not match up", size=(37, 0))
    ],
    [
        sg.Text("PIX Log:")
    ],
    [
        sg.Listbox(values=[], size=(47, 6), key="_PIX LIST_")
    ],
    [
        sg.Text("BGU Log:")
    ],
    [
        sg.Listbox(values=[], size=(47, 6), key="_BGU LIST_")
    ],
    [
        sg.Text("Other Logs:")
    ],
    [
        sg.Listbox(values=[], select_mode=SELECT_MODE_EXTENDED, size=(47, 6), key="_LOG LIST_")
    ],
    [
        sg.Button("COMBINE", key="_COMBINE BUTTON_"),
        # sg.Button("OPEN COMBO LOG IN MISSION PLANNER", key="_MISSION PLANNER BUTTON_")
    ]
]

layout = [
    [
        sg.Column(download_column),
        sg.VSeperator(),
        sg.Column(convert_column),
        sg.VSeperator(),
        sg.Column(combine_column)
    ]
]


class Aggregator:

    def __init__(self, window):
        self.window = window
        self.base_path = ""
        self.fnames = []
        self.flights = []

    def main_window_loop(self):
        while True:
            event, values = self.window.read()
            if event == "Exit" or event == sg.WIN_CLOSED:
                break

            if event == "_FOLDER_":
                self.base_path = values["_FOLDER_"]
                self.update_fnames()

            elif event == "_GET LOGS BUTTON_":
                self.get_logs()

            elif event == "_DOWNLOAD BUTTON_":
                if not values["_PI FILE LIST_"]:
                    self.invoke_error("Select Flight to Download")
                    continue

                if not values["_FLIGHT NAME_"]:
                    self.invoke_error("Input Flight Name")
                    continue

                bg_thread = threading.Thread(target=self.download_logs, args=(values["_PI FILE LIST_"],
                                                                              values["_FLIGHT NAME_"]))
                self.loading_anim(bg_thread, "Downloading")

            elif event == "_CONVERT BUTTON_":
                if not values["_FILE LIST_"]:
                    continue

                bg_thread = threading.Thread(target=self.convert_files, args=(values["_FILE LIST_"],))
                self.loading_anim(bg_thread, "Converting")

                self.move_logs()
                self.update_fnames()

            elif event == "_COMBINE BUTTON_":
                if not values["_PIX LIST_"] or not values["_BGU LIST_"]:
                    self.invoke_error("Select PIX Log AND BGU Log")
                    continue

                if not values["_TIME OFFSET_"]:
                    offset = 0
                else:
                    try:
                        offset = int(values["_TIME OFFSET_"])
                    except ValueError:
                        self.invoke_error("Invalid Time Offset")
                        continue

                combo_log = "{}/{}".format(self.base_path, values["_PIX LIST_"][0][:-4] + "-combo.log")
                pix_log = "{}/{}".format(self.base_path, values["_PIX LIST_"][0])
                bgu_log = "{}/{}".format(self.base_path, values["_BGU LIST_"][0])
                other_logs = " ".join(['"{}/'.format(self.base_path) + x + '"' for x in values["_LOG LIST_"]])

                bg_thread = threading.Thread(target=self.combine_files,
                                             args=(combo_log, pix_log, bgu_log, other_logs, offset))
                self.loading_anim(bg_thread, "Combining")
                self.update_fnames()

            # elif event == "_MISSION PLANNER BUTTON_":
            #     if not values["_FOLDER_"]:
            #         continue
            #
            #     mp_thread = threading.Thread(target=self.open_mp(), args=())
            #     mp_thread.start()
            #     mp_thread.join()

    def move_logs(self):
        for file in os.listdir(os.path.join(self.base_path, "logs")):
            if file[-3:] != "dat":
                shutil.copy(os.path.join(self.base_path, "logs", file), os.path.join(self.base_path, file))

    def update_fnames(self):
        try:
            file_list = os.listdir(self.base_path)
        except FileNotFoundError:
            file_list = []

        self.fnames = [f for f in file_list if os.path.isfile(os.path.join(self.base_path, f))]

        self.window["_PIX LIST_"].update([x for x in self.fnames if not x.endswith(".xz")])
        self.window["_FILE LIST_"].update([x for x in self.fnames if not x.endswith(".xz")])

        self.window["_BGU LIST_"].update([x for x in self.fnames if x.endswith(".bin")])
        self.window["_LOG LIST_"].update([x for x in self.fnames if x.endswith(".bin")])

    def loading_anim(self, pthread, msg):
        pthread.start()
        self.window.Hide()
        while pthread.is_alive():
            sg.popup_animated("Loading.gif", message=msg, no_titlebar=False, icon="Hoverfly-Tech.ico", title="Hoverfly")
            time.sleep(0.05)
        pthread.join()
        self.window.UnHide()
        sg.popup_animated(image_source=None)

    def convert_files(self, files):
        subprocess.call("java -jar \"{}/LogMinion.jar\" -s {} {}".format(os.getcwd().replace("\\", "/"),
                                                                         self.base_path,
                                                                         " ".join(files)), shell=True)

    def combine_files(self, combo_log, pix_log, bgu_log, other_logs, offset):
        if other_logs:
            subprocess.call("DFParser.exe \"{}\" \"{}\" -a \"{}\" -f {} -d GPS -t {}"
                            .format(combo_log, pix_log, bgu_log, other_logs, offset), shell=True)
        else:
            subprocess.call("DFParser.exe \"{}\" \"{}\" -a \"{}\" -d GPS -t {}"
                            .format(combo_log, pix_log, bgu_log, offset), shell=True)

    def login_to_pi(self):
        webAddr = "http://10.20.30.200"

        browser = mechanicalsoup.StatefulBrowser()
        browser.open(webAddr)

        browser.select_form()
        browser["UserName"] = "admin"
        browser["Password"] = "admin"

        resp = browser.submit_selected()
        return browser

    def download_logs(self, file, flight_name):
        ddir = os.path.expandvars(r'%HOMEPATH%\Desktop\HFLogs')
        fdir = "{}\\{}".format(ddir, flight_name)
        logName = ""

        if not os.path.exists(ddir):
            os.mkdir(ddir)

        if not os.path.exists(fdir):
            os.mkdir(fdir)

        browser = self.login_to_pi()
        browser.open('http://10.20.30.200/Logs/ViewLogs?logType=all')

        for flight in self.flights:
            if flight[0] == file[0]:
                for i, log in enumerate(flight):

                    match = re.search('(?<=\.)(.*)', log)
                    if i == 0:
                        if match:
                            logName = "{}_FMS.{}".format(flight_name, match.group(0))
                    elif i == 1:
                        if match:
                            logName = "{}_BGU.{}".format(flight_name, match.group(0))
                    elif i == 2:
                        logName = log
                    elif i == 3:
                        if match:
                            logName = "{}_HUE.{}".format(flight_name, match.group(0))
                    elif i == 4:
                        if match:
                            logName = "{}_BARO.{}".format(flight_name, match.group(0))
                    elif i == 5:
                        if match:
                            logName = "{}_HUD.{}".format(flight_name, match.group(0))

                    browser.download_link(browser.find_link(url_regex=log), "{}\\{}".format(fdir, logName))

        self.unzip_logs(fdir)

    def unzip_logs(self, fdir):
        for file in os.listdir(fdir):
            if file[-3:] != ".xz":
                continue

            with lzma.open(os.path.join(fdir, file)) as infile, open(os.path.join(fdir, file[:-3]), 'wb') as outfile:
                file_content = infile.read()
                outfile.write(file_content)

    def get_logs(self):
        browser = self.login_to_pi()

        browser.open('http://10.20.30.200/Logs/ViewLogs?logType=all')
        page = browser.page

        fmsList = []
        bguDataList = []
        bguServerList = []
        hubLogList = []
        data = [fmsList, bguDataList, bguServerList, hubLogList]
        tables = page.find_all('table')
        passLoop = False
        self.flights = []

        for i in range(len(tables)):
            rows = tables[i].find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                cols = [ele.text.strip() for ele in cols]

                for item in cols:
                    if item == "desktop.ini.xz":
                        passLoop = True

                if not passLoop:
                    data[i].append([ele for ele in cols if ele])

                passLoop = False

        offset = 0

        for i in range(1, len(data[0])):
            fmsLog = data[0][i][1]
            bguDataLog = data[1][i][1]
            bguServerLog = data[2][i][1]
            baroLog = data[3][i + offset][1]
            hubDataLog = data[3][i + offset + 1][1]
            hubEventLog = data[3][i + offset + 2][1]

            self.flights.append([fmsLog, bguDataLog, bguServerLog, baroLog, hubDataLog, hubEventLog])
            offset += 2

        self.window["_PI FILE LIST_"].update([f[0] for f in self.flights])
        browser.close()

    # Can't get Mission Planner to open without freezing the Log Tool
    # def open_mp(self):
    #     combos = 0
    #     for file in os.listdir(self.base_path):
    #         if file[-10:] == "-combo.log":
    #             if combos > 2:
    #                 self.invoke_error("Too many Combo files, only opening 2")
    #                 return
    #             try:
    #                 os.system(r'C:\"Program Files (x86)\Mission Planner\MissionPlanner.exe" "{}\{}"'
    #                           .format(self.base_path, file))
    #                 combos += 1
    #             except FileNotFoundError:
    #                 self.invoke_error("No Mission Planner Found")
    #                 return
    #
    #     if not combos:
    #         self.invoke_error("No Combo Logs Found")
    #         return

    def invoke_error(self, msg):
        sg.popup_error(msg)


if __name__ == '__main__':
    new_window = sg.Window("Hoverfly Data Log Tool", layout, icon="Hoverfly-Tech.ico")
    main_window = Aggregator(new_window)
    main_window.main_window_loop()
