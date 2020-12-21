
import PySimpleGUI as sg
from PySimpleGUI import SELECT_MODE_EXTENDED
import os
import subprocess
import threading
import time
import shutil

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

    def main_window_loop(self):
        while True:
            event, values = self.window.read()
            if event == "Exit" or event == sg.WIN_CLOSED:
                break

            if event == "_FOLDER_":
                self.base_path = values["_FOLDER_"]
                self.update_fnames()

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

        self.window["_PIX LIST_"].update(self.fnames)
        self.window["_FILE LIST_"].update(self.fnames)

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
            subprocess.call("python DFParser.py \"{}\" \"{}\" -a \"{}\" -f {} -d GPS -t {}"
                            .format(combo_log, pix_log, bgu_log, other_logs, offset), shell=True)
        else:
            subprocess.call("python DFParser.py \"{}\" \"{}\" -a \"{}\" -d GPS -t {}"
                            .format(combo_log, pix_log, bgu_log, offset), shell=True)

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
