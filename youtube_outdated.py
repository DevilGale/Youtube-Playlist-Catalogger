from datetime import datetime
import logging
import requests
import json
import math
import os

global global_count
global deleted_songs

#Set up logging
logging.basicConfig(level=logging.DEBUG) #DEBUG / INFO
console_logger = logging.getLogger(__name__)

API_KEY = 
my_channel = 
base_URL = 'https://www.googleapis.com/youtube/v3'

def main():
    global global_count
    global deleted_songs
    deleted_songs = {}
    playlist_set = set()

    # Read youtube file
    if os.path.isfile('./youtube_playlist.tsv'):
        with open('youtube_playlist.tsv', 'r', encoding="utf8") as readFile:
            whole_string = readFile.read()
        array_string = whole_string.split("\n")
        controller = youtube_container(array_string)
    
    #--------------------------
    # Get playlists
    controller.setRequest('{}/playlists?part=id&channelId={}&key={}&maxResults={}'.format(base_URL, my_channel,API_KEY, '50'))
    controller.APIgetPlaylist()

    #--------------------------
    #Gets each video
    controller.loopPlaylists()
    
    #--------------------------
    #Posts changes to logger file
    controller.processPlaylistDifferences()
    controller.loggerFileAppend()

    #-------------------------
    #update file containing video/playlists
    controller.updateTSVfile()

    type_in = input(">>> ")
    while(type_in != "exit"):
        try:
            print(str(eval(type_in)))
        except AttributeError as e:
            console_logger.error(e, exc_info=True)
        except TypeError as e:
            console_logger.error(e, exc_info=True)
        type_in = input(">>> ")

def prettyDictPrint(dict):
    for key in dict.keys():
        console_logger.debug(key)
        if type(dict[key]) == type({}):
            prettyDictPrint(dict[key])
        else:
            if type(dict[key]) == type(set()):
                console_logger.debug("\t\t{}".format(", ".join(dict[key])))
            else:
                console_logger.debug(dict[key])

class youtube_container:
    def __init__(self, array_string):
        #previous run items
        self.previous_dict_list = {}
        self.parsePreviousList(array_string)
        #current run items
        self.current_dict_list = {}
        #API request string
        self.request_str = ""
        #Changed Videos
        self.added_songs = {}
        self.removed_songs = {}
        self.deleted_songs = {}

    def parsePreviousList(self, array_string):
        for line in array_string:
            if line == "":
                continue
            if "\t" not in line:
                self.previous_dict_list[line] = {}
                current_playlist = line
            else:
                contents = line.split("\t")
                # (0)Index -> (1)ID -> (2)Title
                self.previous_dict_list[current_playlist][contents[1]] = (contents[0],contents[2])

    def setRequest(self, request):
        self.request_str = request

    def getPreviousDictList(self):
        return self.previous_dict_list

    def getCurrentDictList(self):
        return self.current_dict_list

    def getAddedSongs(self):
        return self.added_songs

    def getRemovedSongs(self):
        return self.removed_songs

    def getDeletedSongs(self):
        return self.deleted_songs

    #Gets all the playlists for the user
    def APIgetPlaylist(self, nextToken=""):
        r = requests.get(self.request_str + nextToken).json()
        for item in r['items']:
            self.current_dict_list[(item['id'])] = {}
        if 'nextPageToken' in r.keys():
            APIgetPlaylist("&pageToken={}".format(r['nextPageToken']))

    #Loops through each playlist populating the dictionary for each playlist_ID
    def loopPlaylists(self):
        fields_bit = 'nextPageToken, pageInfo,items(snippet(title,position,resourceId(videoId)))'
        for playlist_ID in self.current_dict_list.keys():
            global global_count
            global_count = 0
            self.request_str = '{}/playlistItems?part=snippet&playlistId={}&fields={}&key={}&maxResults={}'.format(base_URL, playlist_ID, fields_bit, API_KEY, 50)
            self.getPlaylistVideos(playlist_ID)

    #Stores the video IDs into the playlist dictionary
    def getPlaylistVideos(self, playlist_ID, nextToken=""):
        global global_count
        global_count += 1
        r = requests.get(self.request_str + nextToken).json()
        #print(json.dumps(r, indent=1))
        print("{}/{}: {}".format(global_count,math.ceil(r['pageInfo']['totalResults']/50),r['pageInfo']))
        ##write_set = []
        for item in r['items']:
            item = item['snippet']
            #Checks if not a new song
            if item['resourceId']['videoId'] in self.previous_dict_list[playlist_ID].keys():
                #Checks if changed name
                if item['title'] != self.previous_dict_list[playlist_ID][item['resourceId']['videoId']][1]:
                    self.deleted_songs[playlist_ID] = (self.previous_dict_list[playlist_ID][item['resourceId']['videoId']][0], [item['resourceId']['videoId']], self.previous_dict_list[playlist_ID][item['resourceId']['videoId']][1])
                    continue
            self.current_dict_list[playlist_ID][item['resourceId']['videoId']] = (item['position'],item['title'])
        #If another page loop again
        if 'nextPageToken' in r.keys():
            self.getPlaylistVideos(playlist_ID, "&pageToken={}".format(r['nextPageToken']))

    # Processes the songs from old to new that have been added or removed
    def processPlaylistDifferences(self):
        #Gets a list of all common playlist IDs
        for playlist_ID in set(self.current_dict_list.keys()).intersection(set(self.previous_dict_list.keys())):
            #Gets a list of songs added to the playlist
            for video_ID in set(self.current_dict_list[playlist_ID].keys()).difference(set(self.previous_dict_list[playlist_ID].keys())):
                if playlist_ID not in self.added_songs.keys():
                    self.added_songs[playlist_ID] = []
                self.added_songs[playlist_ID].append((self.current_dict_list[playlist_ID][video_ID][0], video_ID, self.current_dict_list[playlist_ID][video_ID][1]))
            #Gets a list of songs removed from the playlist
            for video_ID in set(self.previous_dict_list[playlist_ID].keys()).difference(set(self.current_dict_list[playlist_ID].keys())):
                if playlist_ID not in self.removed_songs.keys():
                    self.removed_songs[playlist_ID] = []
                self.removed_songs[playlist_ID].append((self.previous_dict_list[playlist_ID][video_ID][0], video_ID, self.previous_dict_list[playlist_ID][video_ID][1]))

    # Pushes to logger file the updates
    def loggerFileAppend(self):
        if len(self.added_songs.keys()) > 0 or len(self.removed_songs.keys()) > 0 or len(self.deleted_songs.keys()) > 0:
            loggerFile = "<div><li class='log'>{}<hr id='header'>\n".format(datetime.today().strftime("%A, %B %d, %Y"))
            # Prints delete songs
            if len(self.deleted_songs.keys()) > 0:
                loggerFile += self.getVideoLogString(self.deleted_songs, "Deleted")

            # Prints added songs
            if len(self.added_songs.keys()) > 0:
                loggerFile += self.getVideoLogString(self.added_songs, "Added")

            # Prints removed songs
            if len(self.removed_songs.keys()) > 0:
                loggerFile += self.getVideoLogString(self.removed_songs, "Removed")

            loggerFile += "</li></div>"
        #If file doesn't exist do the style
        if not os.path.isfile('./VideoLogger.html'):
            loggerFile = \
            "<style>\n\
                \tbody {\n\
                    \t\tbackground-color: lightgray;\n\
                \t}\n\
                \tdiv {\n\
                    \t\t/*ivory, floralwhite, lightyellow*/\n\
                    \t\tbackground-color: floralwhite;\n\
                    \t\tborder: 1px black solid;\n\
                    \t\tborder-radius: 4px;\n\
                    \t\tmargin: 3px;\n\
                \t}\n\
                \tul, ol {\n\
                    \t\tlist-style: none;\n\
                    \t\tmargin-left: 0;\n\
                    \t\tpadding-left: 0;\n\
                \t}\n\
                \tol {\n\
                    \t\tdisplay: flex;\n\
                    \t\tflex-direction: column-reverse;\n\
                \t}\n\
                \tul li:before \n\
                    \t\t{ content: "├"; padding-right: 0.5em; }\n\
                \tul li:last-child:before \n\
                    \t\t{ content: "└"; padding-right: 0.5em; }\n\
            </style>" + loggerFile
            with open('VideoLogger.html', 'a', encoding="utf8") as file:
                file.write(loggerFile)

    # Template for logging each added, removed, and deleted
    def getVideoLogString(self, dict_list, action_type):
        loopCount = 0
        write_string = "\t<div class='{act}_videos'>{act} Songs<br>\n".format(act=action_type)

        for playlist_ID in dict_list.keys():
            loopCount += 1
            write_string += "\t<ul class='playlist_ul'>{}:<a href='https://www.youtube.com/playlist?list={}'>Playlist</a>\n".format(loopCount, playlist_ID)
            for video_ID in dict_list[playlist_ID]:
                # video_ID = (position, Title)
                #write_string += "<li>{}:<a href='https://www.youtube.com/playlist?list={}'>Playlist</a> - ".format(loopCount, playlist_ID)
                print(video_ID)
                write_string += "\t\t<li>Position {}:<a href='https://www.youtube.com/watch?v={}'>{}</a></li>\n".format(video_ID[0], video_ID[1], video_ID[2])
            write_string += "\t</ul></div>\n"
        return write_string

    def updateTSVfile(self):
        string_write = []
        for playlist_ID in self.current_dict_list.keys():
            string_write.append(playlist_ID)
            for video_ID in self.current_dict_list[playlist_ID].keys():
                video_info = self.current_dict_list[playlist_ID][video_ID]
                string_write.append("{pos}\t{vid_ID}\t{title}".format(pos=video_info[0], vid_ID=video_ID, title=video_info[1]))
            string_write.append("")

        print("---\nWriting to file")
        with open('youtube_playlist.tsv', 'w', encoding="utf8") as file:
            file.write("\n".join(write_string))

main()