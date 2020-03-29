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
#import random

def add_user(username):
    """" Gets auth token and adds user to USERLIST under key = name
    Invokes an external config file for security reasons"""
    global USERLIST
    if username in USERLIST:
        print("ERROR\\ User already added.")
    else:
        CLIENT_ID,CLIENT_SECRET,REDIRECT,USER_NAME = config.get_spotify_info(username)
        scope = "user-modify-playback-state user-read-playback-state"
        token = util.prompt_for_user_token(USER_NAME, scope,CLIENT_ID,CLIENT_SECRET,REDIRECT)
        client = spotipy.Spotify(auth=token)
        USERLIST[username] = (client, parse_current_playback(client,username))
        print(USERLIST[username])
    return USERLIST

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
        print("DEBUG: ",name," is playing ad or nothing type")
        return (False,None,None), 0 #placeholder data for stopped client
    
def detect_change(name,is_leader=False):
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
    global USERLIST, SLEEP_TIME, prevtime
    TOLERANCE = 0.5 #seconds
    client = USERLIST[name][0]
    old_state, oldprog = USERLIST[name][1]
    new_state, newprog = parse_current_playback(client,name)
    USERLIST[name] = (USERLIST[name][0], (new_state, newprog))    
    if is_leader: #timecheck must happen as soon after new state assignment as possible
        if new_state[0] == old_state[0] == False:
            elapsed = 0
        else:
            elapsed = time.perf_counter() - prevtime
        prevtime = time.perf_counter()
        #print("DEBUG: ",round(elapsed,3)," seconds since last leadercheck")
        if abs(newprog - oldprog) > abs((elapsed+TOLERANCE)*1000):
            if new_state[1] != old_state[1]:
                return 'trackchange_event'
            else:
                print("skip detected from leader ",name," of", (newprog - oldprog)/1000, "seconds")
                return 'seek_event'
    if new_state == old_state:
        return False
    else:
        if new_state[1] == old_state[1]:
            return 'pause_event'
        else:
            return 'trackchange_event'

def set_to_state(leader,follower_list,event_type):
    global USERLIST, SLEEP_TIME
    time.sleep(SLEEP_TIME)
    leader_state, leader_uri, _ = USERLIST[leader][1][0]
    leader_prog = USERLIST[leader][1][1]
    if leader_state == None:
        return #do nothing if leader is playing nothing (i.e. if they quit)
    
    for follower in follower_list:
        client = USERLIST[follower][0]
        if event_type == 'seek_event':
            client.pause_playback()
            client.seek_track(leader_prog)
            if leader_state == True: #if playing
                client.start_playback()
        elif event_type == "trackchange_event":
            client.start_playback(uris = [leader_uri],position_ms=leader_prog)
        else:
            print(event_type)
            print("ERROR: Nonetype detected for leaderstate in improper location")
        detect_change(follower)
    return


#wrap this up in nice CLI later
def main():
    global USERLIST, prevtime, SLEEP_TIME
    USERLIST = {}
    done = False
    add_user("mrsnail4") # DEBUG
    # while not done:
    #     user_input = input("Enter username (leave blank if done): ")
    #     if not user_input:
    #         done = True
    #     else:
    #         add_user(user_input)
    namelist = list(USERLIST.keys())
    SLEEP_TIME = 0.5/len(namelist) #0.5s between API pings (is this the right way to do things?)
    
    leader = sorted(namelist, key = lambda x : USERLIST[x][1][1])[0]
    follower_list = namelist[:namelist.index(leader)] + namelist[namelist.index(leader) + 1:]
    prevtime = time.perf_counter()
    #MAINLOOP
    while True:
        time.sleep(SLEEP_TIME)
        leader_event = detect_change(leader,True)
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
                time.sleep(SLEEP_TIME)
                
if __name__ == '__main__':
    main()
"""
LIST OF JANK
janky login

?
issue if no active devices
doesnt work with podcasts


!
only leader can scroll back/forwards within same track
newtrack jank
"""
