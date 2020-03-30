# -*- coding: utf-8 -*-
"""
Created on Sun Mar 29 11:39:44 2020

@author: Hal

DATA STRUCTURES GUIDE
    USER in USERLIST {}:
        (client, PLAYBACK_DATA)
    PLAYBACK_DATA:
        (Current state, track URI, track name), time)
    
for example:
    (<spotipy.client.Spotify object>, ((True, 'spotify:track:6TAW00MAPvS59yEoIgtOEI', 'All Alone'), 619))
"""
import spotipy
import spotipy.util as util
import time
import config
# import random

#------------------ GLOBAL VARIABLES ----------------

global TOLERANCE, USERLIST, timing_dict, SMALL_SLEEP
SMALL_SLEEP = 0.4 #time between pings, this is triggered at the start of the set_state AND detect_state functions
TOLERANCE = 0.5 #maximum permissible desync (seconds)
USERLIST = {}
timing_dict = {}

#------------------- AUTH FUNCTION -----------------

def add_user(username):
    """" Gets auth token and adds user to USERLIST under key = name
    Invokes an external config file for security reasons"""
    global USERLIST
    if username in USERLIST:
        print("ERROR\\ User already added. Skipping...")
    else:
        CLIENT_ID,CLIENT_SECRET,REDIRECT,USER_NAME = config.get_spotify_info(username)
        scope = "user-modify-playback-state user-read-playback-state"
        token = util.prompt_for_user_token(USER_NAME, scope,CLIENT_ID,CLIENT_SECRET,REDIRECT)
        client = spotipy.Spotify(auth=token)
        USERLIST[username] = (client, parse_current_playback(client,username))
        print(USERLIST[username])
    return USERLIST

#-------------- LIVE MONITORING/REACTION --------------
    
def parse_current_playback(client,name):
    """"Gets relevant information about users current playback
    Information recorded: 
        is_playing = True/False/None --> Playing/Paused/Stopped
        track_URI = spotify URI of current track
        track_name = name of current track (mostly for debug purposes)
        prog = number of milliseconds into track
        
    Data returned as ((is_playing,track_URI,track_name), prog)
    """
    raw_info = client.current_playback()
    if raw_info and raw_info['item']:
        #note that despite the variable names this should work for podcast episodes also
        track_URI = raw_info['item']['uri']
        track_name = raw_info['item']['name']
        is_playing = raw_info['is_playing']
        ms_in = raw_info['progress_ms']
        return (is_playing,track_URI,track_name), ms_in
    else:
        return (None,None,None), 0 #placeholder data for stopped client
    
def detect_change(name,update_only=False):
    global USERLIST, SMALL_SLEEP, timing_dict
    """
    Checks if the current state has changed since the last time it was checked
    the key complexity here is that the "prog" (time) variable is always going
    to be changing if the track is playing, so the elapsed time since the last
    check has to be taken into account
    
    1) Measure current time
    2) Compare to previous time to get elapsed time since last check
    3) If the change in time is greater than elapsed time + tolerance, detect change (seek)
    Otherwise log new time and declare "no change"
    """
    time.sleep(SMALL_SLEEP)
    client = USERLIST[name][0]
    old_playback_data, oldprog = USERLIST[name][1]
    new_playback_data, newprog = parse_current_playback(client,name)
    USERLIST[name] = (USERLIST[name][0], (new_playback_data, newprog))
    if update_only:
        timing_dict[name] = time.perf_counter()
        return 'update_event' #stop execution early and return here
    else:
        return determine_event_type(name,old_playback_data, oldprog, new_playback_data, newprog)
    
def determine_event_type(name,old_playback_data, oldprog, new_playback_data, newprog):
    global TOLERANCE
    old_state, old_track, _ = old_playback_data
    new_state, new_track, _ = new_playback_data
    event_type = 'unknown' #default
    if old_track != new_track: 
        event_type = 'trackchange_event'
    else:
        if (not new_state) and (not old_state):
            elapsed = 0 #track has been paused so we expect no time to have elapsed
        else:
            elapsed = time.perf_counter() - timing_dict[name]
            
        if abs(newprog - oldprog) > abs((elapsed+TOLERANCE)*1000):
            event_type = 'seek_event'
        elif new_state != old_state:
            if new_state:
                event_type = 'start_event'
            else:
                event_type = 'stop_event'
        else:
            print("Elapsed since last ping: ",elapsed)
            event_type = False #nothing
    timing_dict[name] = time.perf_counter()       
    return event_type

def set_to_state(leader,follower_list,event_type):
    global USERLIST, SMALL_SLEEP, timing_dict
    """Given a leader and a list of followers,
    make all followers copy the leader"""
    leader_state, leader_uri, _ = USERLIST[leader][1][0]
    leader_prog = USERLIST[leader][1][1]
    trigger_time = timing_dict[leader] #when the desired leader state was measured
    if leader_state == None:
        return #do nothing if leader is playing nothing (i.e. if they quit)
    
    for follower in follower_list:
        time.sleep(SMALL_SLEEP)
        client = USERLIST[follower][0]
        try:
            client.pause_playback()
        except:
            #if no active devices are found (eg: app is closed mid-switch)
            print("DEBUG: Inactive follower ",follower," skipped")
        adjusted_prog = leader_prog + (time.perf_counter() - trigger_time)*1000 #take into account that we spent time setting previous followers
        #adjusted_prog = leader_prog + (time.perf_counter() - trigger_time)*1000
        if event_type == 'seek_event':
            client.seek_track(adjusted_prog)
            if leader_state == True: #if playing
                client.start_playback()
        elif event_type == "trackchange_event":
            client.start_playback(uris = [leader_uri],position_ms=adjusted_prog)
        elif event_type == "unpause_event":
            try:
                client.start_playback(uris = [leader_uri],position_ms=adjusted_prog)
            except:
                print("ERROR: Follower ",follower," not active/cant be reached for unpause_event, skipped...")
        elif event_type == 'pause_event':
            client.pause_playback()
        else:
            print("Failed to parse event:", event_type)
        detect_change(follower,True)
    return


#------------------- DRIVER FUNCTION -----------------
#wrap this up in nice CLI later
def main():
    global USERLIST, timing_dict,DEBUG_TIMING_ERROR
    #add_user("mrsnail4") # DEBUG
    done = False
    while not done:
        user_input = input("Enter username (leave blank if done): ")
        if not user_input:
            done = True
        else:
            add_user(user_input)
    namelist = list(USERLIST.keys())
    leader = sorted(namelist, key = lambda x : USERLIST[x][1][1])[0]
    follower_list = namelist[:namelist.index(leader)] + namelist[namelist.index(leader) + 1:]
        
    for name in namelist:
        timing_dict[name] = time.perf_counter()

    #MAINLOOP
    while True:       
        leader_event = detect_change(leader)
        if leader_event:
            print(leader_event, " from ",leader)
            print(USERLIST[leader])
            #follower_list = [i for i in namelist if i != leader] #readable version
            follower_list = namelist[:namelist.index(leader)] + namelist[namelist.index(leader) + 1:] #fast version
            set_to_state(leader,follower_list,leader_event)
        else:
            for follower in follower_list:
                follower_event = detect_change(follower)
                if follower_event:
                    print(follower_event, " from ",follower)
                    leader = follower
                    follower_list = namelist[:namelist.index(leader)] + namelist[namelist.index(leader) + 1:] #fast version
                    set_to_state(leader,follower_list,follower_event) #confusingly, the "follower_event" is the new "leader_event"
                    break
    return
                
if __name__ == '__main__':
    main()
"""
LIST OF JANK
janky login

?
issue if no active devices
doesnt work with podcasts


!
unpauses itself all the time
sometimes tries to pause when already paused
newtrack jank
while LEADER is PLAYING and FOLLOWER switches tracks, crash with no active device found
if PAUSE: Nonetype Detected

incorporate fixed delay on new track

seek instead of changetrack following nonetype error
"""
