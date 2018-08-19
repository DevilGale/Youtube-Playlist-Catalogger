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
        # Holds playlist IDs holding video IDs
        dict_list = {}
        # Holds
        video_set = {}
        for line in array_string:
            if line == "":
                continue
            if "\t" not in line:
                dict_list[line] = {}
                video_set[line] = set()
                current_playlist = line
            else:
                contents = line.split("\t")
                dict_list[current_playlist][contents[1]] = (contents[0],contents[2])
                video_set[current_playlist].add(contents[1])
        #prettyDictPrint(dict_list)
        #prettyDictPrint(video_set)
    
    #--------------------------
    # Get playlists
    controller.setRequest('{}/playlists?part=id&channelId={}&key={}&maxResults={}'.format(base_URL, my_channel,API_KEY, '50'))
    controller.APIgetPlaylist()

    r = requests.get('{}/playlists?part=id&channelId={}&key={}&maxResults={}'.format(base_URL, my_channel,API_KEY, '50')).json()
    for item in r['items']:
        playlist_set.add(item['id'])
    if 'nextPageToken' in r.keys():
        r = requests.get('{}/playlists?part=id&pageToken={}&channelId={}&key={}&maxResults={}'.format(base_URL,r['nextPageToken'], my_channel,API_KEY, 50)).json()
        for item in r['items']:
            playlist_set.add(item['id'])
        #print(json.dumps(r, indent=1))
    print(playlist_set)

    #--------------------------
    #Gets each video
    controller.loopPlaylists()
    fields_bit = 'nextPageToken, pageInfo,items(snippet(title,position,resourceId(videoId)))'
    write_string = []
    new_playlist_videos = set()
    loggerFile = ""
    while len(playlist_set) != 0:
        new_playlist_videos.clear()
        global_count = 0
        playlist_item = playlist_set.pop()
        write_string.append(playlist_item)
        input_str = '{}/playlistItems?part=snippet&playlistId={}&fields={}&key={}&maxResults={}'.format(base_URL, playlist_item,fields_bit,API_KEY, 50)
        # Getting each video
        # Goes through whole playlist
        result_list, result_vids = getPlaylistItems(dict_list[playlist_item], input_str)
        write_string += result_list
        new_playlist_videos.update(result_vids)
        write_string.append("")

        if playlist_item in video_set.keys():
        
            added_songs = list(new_playlist_videos.difference(video_set[playlist_item]))
            removed_songs = list(video_set[playlist_item].difference(new_playlist_videos))
            
            console_logger.info(">>> {} <<<".format(playlist_item))
            #Current - Past
            console_logger.info("--- Added Songs ---")
            console_logger.info(added_songs)
            
            #Past - Current
            console_logger.info("--- Removed Songs ---")
            console_logger.info(removed_songs)
            
            if len(added_songs) > 0 or len(removed_songs) > 0:
                loggerFile += "<p><a href='https://www.youtube.com/playlist?list={}'>Playlist</a>\n".format(playlist_item)
                if len(added_songs) > 0:
                    loggerFile += "\t<br>Added Songs<br><ul>\n"
                    for ID in added_songs:
                        if ID == "":
                            break
                        loggerFile += "\t\t<li><a href='https://www.youtube.com/watch?v={}'>Link</a></li>\n".format(ID)
                    loggerFile += "\t</ul>\n"
                if len(removed_songs) > 0:
                    loggerFile += "\t<br>Removed Songs<br><ul>\n"
                    for ID in removed_songs:
                        print("Remove: {}".format(ID))
                        if ID == "":
                            break
                        elif ID in deleted_songs.keys():
                            continue
                        loggerFile += "\t\t<li><a href='https://www.youtube.com/watch?v={}'>{}</a></li>\n".format(ID, dict_list[playlist_item][ID][1])
                    loggerFile += "\t</ul>\n"
                loggerFile += "</p>\n"
            if len(deleted_songs.keys()) > 0:
                loggerFile += "\t<br>Deleted Songs<br><ul>\n"
                for ID in deleted_songs.keys():
                    loggerFile += "\t\t<li><a href='https://www.youtube.com/watch?v={}'>{}</a></li>\n".format(ID, deleted_songs[ID])
                loggerFile += "\t</ul>\n"

    if loggerFile != "":
        #If file doesn't exist do the style
        if not os.path.isfile('./VideoLogger.html'):
            style_string =                      \
            "<style>                            \n\
            div {                               \n\
            \t  border: 1px black solid;        \n\
            \t  border-radius: 5px;             \n\
            }                                   \n\
            </style>\n"
            style_string += "<ol id='log'>\n"
        else:
            #li:before 
            #{ content: "├"; padding-right: 1em; }
            #li:last-child:before 
            #{ content: "└"; padding-right: 1em; }
            style_string = ""
        with open('VideoLogger.html', 'a', encoding="utf8") as file:
            loggerFile = "{}<li><div>{}<hr id='header'>".format(style_string, datetime.today().strftime("%A, %B %d, %Y")) + loggerFile + "</div>"
            file.write(loggerFile)

                # border: 1px black solid;
                # padding: 2px 10px;
                # border-radius: 7px;
                # background: lightyellow;
    #print(write_string)

    if not os.path.isfile('./youtube_playlist.tsv'):
        print("---\nWriting to file")
        with open('youtube_playlist.tsv', 'w', encoding="utf8") as file:
            file.write("\n".join(write_string))

    type_in = input(">>> ")
    while(type_in != "exit"):
        try:
            print(str(eval(type_in)))
        except AttributeError as e:
            console_logger.error(e, exc_info=True)
        except TypeError as e:
            console_logger.error(e, exc_info=True)
        type_in = input(">>> ")



def getPlaylistItems(playlist_previous_vids, request_str,nextToken=""):
    global global_count
    global deleted_songs
    global_count += 1
    r = requests.get(request_str + nextToken).json()
    #print(json.dumps(r, indent=1))
    print("{}/{}: {}".format(global_count,math.ceil(r['pageInfo']['totalResults']/50),r['pageInfo']))
    write_string = []
    write_set = []
    for item in r['items']:
        item = item['snippet']
        write_string.append("{}\t{}\t{}".format(item['position'], item['resourceId']['videoId'], item['title']))
        write_set.append(item['resourceId']['videoId'])
        if item['resourceId']['videoId'] in playlist_previous_vids.keys():
            if item['title'] != playlist_previous_vids[item['resourceId']['videoId']][1]:
                console_logger.debug("Deleted Song (Mismatch): {}".format(playlist_previous_vids[item['resourceId']['videoId']][1]))
                deleted_songs[item['resourceId']['videoId']] = item['title']
    if 'nextPageToken' in r.keys():
        add_string, add_set = getPlaylistItems(playlist_previous_vids, request_str,"&pageToken={}".format(r['nextPageToken']))
        return (write_string + add_string), (write_set + add_set)
    else:
        return write_string, write_set
    

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
        self.previous_set_list = {}
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
                self.previous_set_list[line] = set()
                current_playlist = line
            else:
                contents = line.split("\t")
                # (0)Index -> (1)ID -> (2)Title
                self.previous_dict_list[current_playlist][contents[1]] = (contents[0],contents[2])
                self.previous_set_list[current_playlist].add(contents[1])

    def setRequest(self, request):
        self.request_str = request

    def getPreviousDictList(self):
        return self.previous_dict_list

    def getPreviousSetList(self):
        return self.previous_set_list

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
            ##write_string.append("{}\t{}\t{}".format(item['position'], item['resourceId']['videoId'], item['title']))
            ##write_set.append(item['resourceId']['videoId'])
            if item['resourceId']['videoId'] in self.previous_dict_list[playlist_ID].keys():
                if item['title'] != self.previous_dict_list[playlist_ID][item['resourceId']['videoId']][1]:
                    self.deleted_songs[playlist_ID] = (self.previous_dict_list[playlist_ID][item['resourceId']['videoId']][0], [item['resourceId']['videoId']], self.previous_dict_list[playlist_ID][item['resourceId']['videoId']][1])
                    continue
            self.current_dict_list[playlist_ID][item['resourceId']['videoId']] = (item['position'],item['title'])
        if 'nextPageToken' in r.keys():
            self.getPlaylistVideos(playlist_ID, "&pageToken={}".format(r['nextPageToken']))

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
            with open('VideoLogger.html', 'a', encoding="utf8") as file:
                file.write(loggerFile)

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
                

main()